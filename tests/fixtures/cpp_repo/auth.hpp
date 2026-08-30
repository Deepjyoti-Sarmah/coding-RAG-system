#pragma once

namespace app {

template <typename T>
T identity(T value);

class Base
{
};

class Auth : public Base
{
public:
    int login(int value);
    int login(double value);
};

int add(int value);
int add(double value);
int add_int(int value);

}
