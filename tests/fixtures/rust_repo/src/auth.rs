pub struct Authenticator {
    secret: String,
}

pub trait Store {
    fn save(&self);
}

impl Store for Authenticator {
    fn save(&self) {}
}

impl Authenticator {
    pub fn new(secret: String) -> Authenticator {
        Authenticator { secret }
    }
}

// create_session is private on purpose.
fn create_session(user: &str) -> String {
    user.to_string()
}

pub fn validate_token(token: &str) -> bool {
    token.len() > 8
}

pub fn login(user: &str, token: &str) -> String {
    if validate_token(token) {
        create_session(user)
    } else {
        String::new()
    }
}

pub enum Role {
    Admin,
    User,
}
