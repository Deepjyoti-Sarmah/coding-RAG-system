package auth;

interface Store {
    void save();
}

// createSession is package-private on purpose.
class SessionFactory {
    static String createSession(String user) {
        return user;
    }
}

public class Authenticator {
    private String secret;

    public Authenticator(String secret) {
        this.secret = secret;
    }

    public static boolean validateToken(String token) {
        return token.length() > 8;
    }

    public String login(String user, String token) {
        if (validateToken(token)) {
            return SessionFactory.createSession(user);
        }
        return "";
    }
}

class PersistentAuthenticator extends Authenticator implements Store {
    PersistentAuthenticator(String secret) {
        super(secret);
    }

    public void save() {
    }
}
