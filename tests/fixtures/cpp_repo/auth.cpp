#include "auth.hpp"

namespace app {

template <typename T>
T identity(T value)
{
    return value;
}

int add(int value)
{
    return value + 1;
}

int add(double value)
{
    return static_cast<int>(value);
}

int add_int(int value)
{
    return add(value);
}

int Auth::login(int value)
{
    return add_int(value);
}

int Auth::login(double value)
{
    return add_int(static_cast<int>(value));
}

int choose()
{
    identity(1);
    add(1);
    add(1.0);
    return 0;
}

int ambiguous(int value)
{
    add(value);
    return 0;
}

void run_method(Auth& auth)
{
    auth.login(1);
}

}
