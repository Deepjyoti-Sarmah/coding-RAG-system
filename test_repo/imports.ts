// Named import
import { login } from "./auth";

// Multiple named imports
import { login, logout } from "./auth";

// Aliased import
import { login as authLogin } from "./auth";

// Default import
import AuthService from "./auth";

// Namespace import
import * as auth from "./auth";

// Mixed import
import Auth, { login, logout as signOut } from "./auth";
