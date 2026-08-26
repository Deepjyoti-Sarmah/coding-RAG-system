package auth

// createSession is unexported on purpose.
func createSession(user string) string {
	return user
}

// ValidateToken is exported.
func ValidateToken(token string) bool {
	return len(token) > 8
}

type Authenticator struct {
	secret string
}

func NewAuthenticator(secret string) *Authenticator {
	return &Authenticator{secret: secret}
}

func (a *Authenticator) Login(user, token string) string {
	if ValidateToken(token) {
		return createSession(user)
	}
	return ""
}

type Store interface {
	Save() error
}
