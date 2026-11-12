import { isRecord, parseChallenge, parseSession } from "./contracts.ts";
import type { OtpRequest, Session } from "./contracts.ts";
import { accountPath } from "./account-routes.ts";
import { validateUpload } from "./media.ts";
import { adminPath, moderationBody } from "./admin-routes.ts";

export class ApiError extends Error {
  status: number;
  retryAfter: number;
  constructor(status: number, message: string, retryAfter = 0) {
    super(message); this.status = status; this.retryAfter = retryAfter;
  }
}
export type AuthState = { session: Session | null; loading: boolean; error: string };
/** One in-memory browser adapter for the existing backend session. Never a new token store. */
export class BrowserClient {
  private state: AuthState = { session: null, loading: true, error: "" };
  private listeners = new Set<() => void>();
  private generation = 0;
  private bootstrapFlight: Promise<Session> | null = null;
  private mutationPending = false;
  private transport: typeof fetch;
  private sessionChangedHandler: () => void = () => {};
  setSessionChangedHandler(handler: () => void) { this.sessionChangedHandler = handler; }
  constructor(transport: typeof fetch = fetch.bind(globalThis)) {
  this.transport = transport;
}
  snapshot = () => this.state;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private update(state: AuthState) { this.state = state; this.listeners.forEach(listener => listener()); }
  invalidate(message = "Your session changed. Please sign in again.") {
    this.generation++; this.bootstrapFlight = null;
    this.update({ session: null, loading: false, error: message });
  }
  private async request(path: string, method = "GET", body?: unknown, csrf?: string): Promise<unknown> {
    if (path.includes("?")) { try { path = path.startsWith("/api/admin/") ? adminPath(method, path) : accountPath(method, path); } catch { throw new ApiError(400, "Invalid API query."); } }
    else if (!/^\/api\/[a-z0-9/._-]+$/i.test(path) || path.includes("..")) throw new ApiError(400, "Invalid API path.");
    const generation = this.generation;
    const headers: Record<string, string> = { "X-LV-Client": "web", Accept: "application/json" };
    if (csrf) headers["X-CSRF-Token"] = csrf;
    if (body !== undefined && !(body instanceof FormData)) headers["Content-Type"] = "application/json";
    let response: Response;
    try { response = await this.transport(path, { method, headers, credentials: "same-origin", cache: "no-store", redirect: "error", body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(body instanceof FormData ? 60000 : 20000) }); }
    catch {
  throw new ApiError(
    0,
    "Unable to connect. Check your connection and try again."
  );
}
    if (generation !== this.generation) throw new ApiError(409, "Your session changed. Please retry.");
    if (response.status === 401) this.invalidate("Your session expired or was revoked. Please sign in again.");
    let data: unknown;
    try { data = await response.json(); } catch { throw new ApiError(response.status, "The service returned an invalid response."); }
    if (response.ok && generation !== this.generation) throw new ApiError(409, "Your session changed. Please retry.");
    if (!response.ok) {
      // Do not reflect arbitrary upstream HTML, exception strings or authentication payloads.
      const messages: Record<number, string> = {
        400: "The request could not be completed. Check your details or request a new code.",
        401: "Your credentials or session are invalid. Please sign in again.",
        403: "Access denied or browser session changed. Reload before trying again.",
        409: "This account cannot be linked automatically. Sign in using your existing method.",
        422: "Check the required fields and enter a valid verification code.",
        429: "Too many attempts. Please wait before trying again.",
        503: "Sign-in is temporarily unavailable. Backend origins, identity configuration or provider access may need attention.",
      };
      throw new ApiError(response.status, messages[response.status] || "The request failed. Please try again.", Math.min(3600, Math.max(0, Number(response.headers.get("retry-after")) || 0)));
    }
    return data;
  }
  async bootstrap(): Promise<Session> {
    if (this.bootstrapFlight) return this.bootstrapFlight;
    const generation = this.generation;
    this.update({ ...this.state, loading: true, error: "" });
    const flight = this.request("/api/auth/browser/bootstrap").then(data => {
      const session = parseSession(data);
      if (generation !== this.generation) throw new ApiError(409, "Session initialization changed.");
      const previous = this.state.session;
      if (previous && (previous.user?.user_id !== session.user?.user_id || previous.csrf_token !== session.csrf_token)) this.generation++;
      this.update({ session, loading: false, error: "" });
      return session;
    }).catch((error: unknown) => {
      if (generation === this.generation) this.update({ session: null, loading: false, error: error instanceof Error ? error.message : "Session initialization failed." });
      throw error;
    }).finally(() => { if (this.bootstrapFlight === flight) this.bootstrapFlight = null; });
    this.bootstrapFlight = flight;
    return flight;
  }
  private async exclusive<T>(action: (csrf: string) => Promise<T>): Promise<T> {
    if (this.mutationPending) throw new ApiError(409, "Another authentication request is in progress.");
    this.mutationPending = true;
    try {
      const generation = this.generation;
      const session = this.state.session || await this.bootstrap();
      if (generation !== this.generation) throw new ApiError(409, "Session changed.");
      return await action(session.csrf_token);
    } finally { this.mutationPending = false; }
  }
  requestOtp(input: OtpRequest) {
    return this.exclusive(async csrf => parseChallenge(await this.request("/api/auth/otp/request", "POST", input, csrf)));
  }
  async account(path: string, method = "GET", body?: unknown) {
    try { path = accountPath(method, path); } catch { throw new ApiError(400, "Unsupported account operation."); }
    const action = async (csrf: string) => {
      if (!this.state.session?.user) throw new ApiError(401, "Sign in to manage your account.");
      try { return await this.request(path, method, body, csrf); }
      catch (error) {
        if (error instanceof ApiError && ![0, 401, 403, 429, 503].includes(error.status)) throw new ApiError(error.status, "This operation could not be completed. Check your details, permissions and the current record status.");
        throw error;
      }
    };
    if (method !== "GET") return this.exclusive(action);
    // Reads remain generation-checked but do not acquire the mutation lock.
    const generation = this.generation;
    const session = this.state.session || await this.bootstrap();
    if (generation !== this.generation) throw new ApiError(409, "Session changed.");
    return action(session.csrf_token);
  }
  async upload(file: File, kind: "property_photo" | "broker_doc") {
    const form = new FormData(); form.set("file", file); form.set("kind", kind); await validateUpload(form);
    return this.exclusive(async csrf => {
      if (!this.state.session?.user) throw new ApiError(401, "Sign in before uploading files.");
      const data = await this.request("/api/uploads", "POST", form, csrf);
      if (!isRecord(data) || typeof data.id !== "string" || !/^[a-zA-Z0-9_-]{1,100}$/.test(data.id) || data.kind !== kind) throw new ApiError(502, "Upload confirmation is invalid.");
      return { id: data.id, url: `/api/files/${data.id}` };
    });
  }
  async admin(path: string, note: string) {
    try { path = adminPath("POST", path); } catch { throw new ApiError(400, "Unsupported administrative operation."); }
    const parts = path.split("/");
    const body = moderationBody(parts.at(-1)!, note);
    return this.exclusive(async csrf => {
      const user = this.state.session?.user;
      if (!user || user.role !== "admin") throw new ApiError(403, "Administrator access is required.");
      if (parts[3] === "brokers" && parts[4] === user.user_id) throw new ApiError(403, "Your own application must be reviewed by another administrator.");
      try {
        const data = await this.request(path, "POST", body, csrf);
        const expected = ({ approve: parts[3] === "listings" ? "active" : "approved", reject: "rejected", "request-changes": "changes_requested", suspend: "suspended", deactivate: "inactive", reactivate: "pending_review" } as Record<string, string>)[parts[5]!];
        if (!isRecord(data) || (parts[3] === "listings" ? data.id !== parts[4] || data.listing_status !== expected : data.status !== expected)) throw new ApiError(502, "The server did not confirm this decision. Refresh before trying again.");
        return data;
      }
      catch (error) {
        if (error instanceof ApiError && ![0, 401, 403, 429, 503].includes(error.status)) throw new ApiError(error.status, "The decision was not saved. Check the record's current status and your permissions.");
        throw error;
      }
    });
  }
  async adminDetail(path: string) {
    path = adminPath("GET", path);
    const generation = this.generation;
    const session = this.state.session || await this.bootstrap();
    if (generation !== this.generation) throw new ApiError(409, "Session changed.");
    if (session.user?.role !== "admin") throw new ApiError(403, "Administrator access is required.");
    return this.request(path);
  }
  async adminOperation(path: string, method: "POST" | "PUT" | "PATCH", body: unknown) {
    try { path = adminPath(method, path); } catch { throw new ApiError(400, "Unsupported administrative operation."); }
    return this.exclusive(async csrf => {
      if (this.state.session?.user?.role !== "admin") throw new ApiError(403, "Administrator access is required.");
      const result = await this.request(path, method, body, csrf);
      if (!isRecord(result) || !(typeof result.id === "string" || result.resolved === true)) throw new ApiError(502, "Save could not be confirmed. Refresh before retrying.");
      return result;
    });
  }
  private accept(data: unknown) {
    const session = parseSession(data);
    if (!session.user) throw new ApiError(502, "Sign-in did not establish an account.");
    this.generation++; this.bootstrapFlight = null;
    this.update({ session, loading: false, error: "" }); this.sessionChangedHandler();
  }
  verifyOtp(challenge_id: string, code: string) {
    if (!/^\d{6}$/.test(code)) return Promise.reject(new ApiError(422, "Enter the six-digit code."));
    return this.exclusive(async csrf => { this.accept(await this.request("/api/auth/otp/verify", "POST", { challenge_id, code }, csrf)); });
  }
  googleNonce(): Promise<string> {
    return this.exclusive(async csrf => {
      const data = await this.request("/api/auth/browser/google-nonce", "POST", {}, csrf);
      if (!isRecord(data) || typeof data.nonce !== "string" || !data.nonce) throw new ApiError(502, "Google sign-in could not be initialized.");
      return data.nonce;
    });
  }
  google(credential: string) {
    if (!credential.trim()) return Promise.reject(new ApiError(400, "Google did not return a credential."));
    return this.exclusive(async csrf => { this.accept(await this.request("/api/auth/google", "POST", { id_token: credential }, csrf)); });
  }
  async logout() {
    return this.exclusive(async csrf => {
      try { await this.request("/api/auth/logout", "POST", {}, csrf); }
      catch (error) {
        this.invalidate("Sign-out could not be confirmed by the server. Retry before leaving this device.");
        this.sessionChangedHandler(); throw error;
      }
      this.invalidate(""); this.sessionChangedHandler();
    });
  }
}
