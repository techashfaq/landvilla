/** Serializes secure-storage writes and invalidates stale async authentication work. */
export class SessionWrites {
  version = 0;
  private pending: Promise<void> = Promise.resolve();
  next() { return ++this.version; }
  current(version: number) { return version === this.version; }
  save(version: number, write: () => Promise<void>) {
    const operation = this.pending.catch(() => {}).then(async () => {
      if (this.current(version)) await write();
    });
    this.pending = operation;
    return operation;
  }
}
