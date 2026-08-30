export function validateToken(token) {
  return Boolean(token);
}

export function login(user, token) {
  return validateToken(token) ? user : null;
}
