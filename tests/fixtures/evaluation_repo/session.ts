import { generateToken } from "./token";

export function createAuthToken(userId: string) {
  return generateToken(userId);
}

export function validateTokenExpiry(token: string) {
  return token.length > 0;
}
