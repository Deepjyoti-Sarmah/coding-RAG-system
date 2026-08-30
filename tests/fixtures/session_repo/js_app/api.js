import { login } from "./auth.js";

export function handleRequest(user, token) {
  return login(user, token);
}
