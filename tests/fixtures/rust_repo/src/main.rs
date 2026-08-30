mod auth;

use crate::auth::Authenticator;
use crate::auth::login;

pub fn handle_request(user: &str, token: &str) -> String {
    let _a = Authenticator::new(String::from("s3cret"));
    login(user, token)
}
