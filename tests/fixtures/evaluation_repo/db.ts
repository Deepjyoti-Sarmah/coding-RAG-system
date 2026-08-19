export function connect() {
  return { connected: true };
}

export function queryUser(id: string) {
  connect();
  return { id, name: "user" };
}
