#include "auth.hpp"

namespace app {

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

}
