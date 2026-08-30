#pragma once

namespace app {

class Base
{
};

class Auth : public Base
{
public:
    int login(int value);
};

int add(int value);
int add(double value);
int add_int(int value);

}
