import "server-only";
import { readConfig } from "./config";
import { publicApi } from "./public-transport";

export function getPublicApi() { return publicApi(readConfig(process.env)); }
