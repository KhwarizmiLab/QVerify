_test = [(0, 0), (0, 1), (1, 0), (1, 1)]


def chsh_corr(RA, RB, BA, BB):
    alice_measurement_choices = BA
    bob_measurement_choices = BB
    count_a1_b1 = [0, 0, 0, 0]
    count_a1_b3 = [0, 0, 0, 0]
    count_a3_b1 = [0, 0, 0, 0]
    count_a3_b3 = [0, 0, 0, 0]
    for i in range(len(RA)):
        valpair = (int(RB[i]), int(RA[i]))
        if alice_measurement_choices[i] == 1 and bob_measurement_choices[i] == 1:
            for j in range(4):
                if _test[j] == valpair:
                    count_a1_b1[j] += 1
        if alice_measurement_choices[i] == 1 and bob_measurement_choices[i] == 3:
            for j in range(4):
                if _test[j] == valpair:
                    count_a1_b3[j] += 1
        if alice_measurement_choices[i] == 3 and bob_measurement_choices[i] == 1:
            for j in range(4):
                if _test[j] == valpair:
                    count_a3_b1[j] += 1
        if alice_measurement_choices[i] == 3 and bob_measurement_choices[i] == 3:
            for j in range(4):
                if _test[j] == valpair:
                    count_a3_b3[j] += 1
    total11 = sum(count_a1_b1)
    total13 = sum(count_a1_b3)
    total31 = sum(count_a3_b1)
    total33 = sum(count_a3_b3)
    # Need nonzero counts in all four CHSH basis pairs; otherwise correlation is undefined.
    if min(total11, total13, total31, total33) == 0:
        return None
    expect11 = (
        count_a1_b1[0] - count_a1_b1[1] - count_a1_b1[2] + count_a1_b1[3]
    ) / total11
    expect13 = (
        count_a1_b3[0] - count_a1_b3[1] - count_a1_b3[2] + count_a1_b3[3]
    ) / total13
    expect31 = (
        count_a3_b1[0] - count_a3_b1[1] - count_a3_b1[2] + count_a3_b1[3]
    ) / total31
    expect33 = (
        count_a3_b3[0] - count_a3_b3[1] - count_a3_b3[2] + count_a3_b3[3]
    ) / total33
    return expect11 - expect13 + expect31 + expect33
