import { validateToken } from "./token";

export function createAuth() {
  return { secret: "s3cr3t" };
}

export function login(username: string) {
  validateToken(username);
  return createAuth();
}

export function logout() {
  return true;
}
