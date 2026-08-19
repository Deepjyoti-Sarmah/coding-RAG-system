export function validateToken(token: string) {
  return token.length > 0;
}

export function generateToken(userId: string) {
  return `token-${userId}`;
}
