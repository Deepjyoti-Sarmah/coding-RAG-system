package main

import (
	"fmt"
	"auth"
)

func HandleRequest(user, token string) string {
	a := auth.NewAuthenticator("s3cret")
	session := a.Login(user, token)
	fmt.Println(session)
	return session
}
