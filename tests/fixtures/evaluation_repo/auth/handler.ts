import { logout } from "../auth";

export function handleAuthCallback() {
  return logout();
}
