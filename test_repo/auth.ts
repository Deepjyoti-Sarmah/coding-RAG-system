export function createAuth() { }

export function validateUser() { }

export function logout() { }

export function login() {
  createAuth();

  auth.createAuth();

  auth.client.createAuth();

  function helper() {
    validateUser();
  }

  logout();
}

export class AuthService {

  login() {
    createAuth();
  }

  logout() {
    logout();
  }
}
