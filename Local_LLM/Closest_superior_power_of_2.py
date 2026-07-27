
def power_of_2(n, pow=2):
    if pow > n:
        return pow
    return power_of_2(n, 2 * pow)


a = int(input("Please enter a number: "))
print(power_of_2(a))
