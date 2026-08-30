package app;

import auth.Authenticator;

public class Main {
    public static String handleRequest(String user, String token) {
        Authenticator a = new Authenticator("s3cret");
        String session = a.login(user, token);
        return session;
    }
}
