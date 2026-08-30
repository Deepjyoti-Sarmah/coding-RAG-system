#include "auth.h"

int authenticate(const char *token)
{
    return validate(token);
}
