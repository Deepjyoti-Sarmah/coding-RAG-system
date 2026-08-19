import { login } from "./auth";
import { queryUser } from "./db";

export function handleRequest(userId: string) {
  const user = queryUser(userId);
  return login(user.name);
}
