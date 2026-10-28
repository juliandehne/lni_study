import pandas as pd
import itertools as it

from scipy.stats import spearmanr
from distance_measures import *
from visualisation import *
from categories import *
from hypothesis_builder import *


def correlator(A, B, percent=True):
    with np.errstate(divide="ignore", invalid="ignore"):

        # Same-option correlation between the coders
        same_option_corr = []
        for j in range(len(A[0])):
            r = np.corrcoef(A[:, j], B[:, j])[0, 1]
            same_option_corr.append(r)

        # Correlate every option of A with every option of B
        if percent:
            M_ = np.full((len(A[0]), len(A[0])), np.nan)

            for j in range(len(A[0])):
                selected = A[:, j] == 1

                if selected.sum() > 0:
                    M_[j] = B[selected].mean(axis=0)
        else:
            M_ = np.corrcoef(A.T, B.T)[:len(A[0]), len(A[0]):]

        # Correlation of how many options each coder chooses
        A_counts = A.sum(axis=1)
        B_counts = B.sum(axis=1)

        rho, p = (spearmanr(A_counts, B_counts)
        if np.std(A_counts) != 0 and np.std(B_counts)
        else (np.nan, np.nan))

        return (np.array(same_option_corr),
                M_,
                (float(rho), float(p)))

def mean_update(old_mean, new_value, count_):
    new_mean = old_mean + (new_value - old_mean) / count_
    return new_mean

def dict_listifier(csv):
    ids = np.array(csv["id"])
    final_category = np.array(csv["final_category"])

    dic = {}
    for index_, id_ in enumerate(ids):
        if id_ in dic:
            dic[id_].append(final_category[index_])
        else:
            dic[id_] = [final_category[index_]]
    return dic

def list_dictifier(lis, Kat):
    buffer = {}
    for ent in lis[Kat]:
        buffer[ent] = 0
    return buffer

def bin_builder(cat_, cor, func, key__, Kategorie_, bin1, bin2, J_list, L_list):

    J_buff, L_buff = [], []
    for sub in cat_:
        cor[sub] += 1 if ((sub in func[0]) or (not sub in func[1])) else 0
        J_buff.append(1 if sub in set(J_list[key__][Kategorie_].split(";")) else 0)
        L_buff.append(1 if sub in set(L_list[key__][Kategorie_].split(";")) else 0)

    bin1.append(J_buff)
    bin2.append(L_buff)

    return

def form(reg, dir_, coder, sub, switch=False):
    string_ = reg[int(switch)].replace(dir_, '').replace(f"{coder};", '')
    conseq = {coder: {sub[int(i)-1] for i in string_.split(',')}}

    string_ = reg[1 - int(switch)].replace(f"{"JL".replace(coder, '')};", '')
    antec = {"JL".replace(coder, ''): {sub[int(i)-1] for i in string_.split(',')}}
    return antec, conseq


if __name__ == '__main__':

    ####################################################################################################################
    # Initialization

    measures = ["disjoint", "subset", "jaccard", "relative_subset"]
    alpha_formula = lambda Do_, De: round(1 - Do_ / De, 4)
    Kategorie = input(f"Welche Subkategrie möchtest du betrachten?\nPick by number:"
                          f"{"".join([f"\n[{i+1}] {kat}" for (i, kat) in enumerate(Kategorien)])} \nchoice: ")

    if not Kategorie in ['1', '2', '3', '4', '5', '6']:
        raise "Error, illegal input!!!"

    Kategorie = int(Kategorie) - 1

    is_multichoice = Kategorie in [2, 3, 4, 5]

    J_dict_list, L_dict_list = (
        dict_listifier(pd.read_csv("Codings/J_coding")),
        dict_listifier(pd.read_csv("Codings/L_coding")))

    ana = 'a' if Kategorie == 0 else input("Möchtest du (a) analysieren oder (b) Hypothese testen?: ").lower()

    if ana == 'b':

        J_copy = J_dict_list.copy()
        J_dict_list = {key: J_dict_list[key][Kategorie]
                       for key in J_dict_list.keys()
                       if (key in L_dict_list
                           and (J_dict_list[key][0] == L_dict_list[key][0] == '1'))}

        L_dict_list = {key: L_dict_list[key][Kategorie]
                       for key in J_copy.keys()
                       if (key in L_dict_list
                           and (J_copy[key][0] == L_dict_list[key][0] == '1'))}


        with (open(f"Hypothesis_Report.txt", "w", encoding="utf-8") as report):
            test_art = input("Möchtest du eine spezielle Regel testen (j), oder alle Regeln der Länge kleiner gleich N (n)?: ").lower()

            if test_art == 'j':

                regel = input("Welche Regel möchtest du testen? (e.g. J;2,4->L;2) "
                      f"{"".join([f"\n[{i + 1}] {subkat}" 
                                  for (i, subkat) in enumerate(Q[Kategorie])])} \nchoice: ").replace(' ', '')
                L_first = regel[0] == "L"
                regel = regel.split('-')

                if L_first:
                    a, c = form(regel, '<', 'L', Q[Kategorie]) if '<' in regel[0] \
                      else form(regel, '>', 'J', Q[Kategorie], True)
                else:
                    a, c = form(regel, '<', 'J', Q[Kategorie]) if '<' in regel[0] \
                      else form(regel, '>', 'L', Q[Kategorie], True)

                if not (len(a[list(a.keys())[0]]) >= 1 and len(c[list(c.keys())[0]]) == 1):
                    raise "Error, illegal input!!!"

                hypothesis = hypothesis_tester(a, c, {'J': J_dict_list, 'L': L_dict_list})
                visualisation_number = max([len(ke) for ke in hypothesis.keys()]) + 1

                print()
                report.write("\n")
                for ke in hypothesis.keys():
                    adjust_num = visualisation_number - len(ke)
                    adjust = "".join([" " for _ in range(adjust_num)])
                    print(adjust + f"{ke}: {hypothesis[ke]}")
                    report.write(adjust + f"{ke}: {hypothesis[ke]}" + "\n")

            elif test_art == "n":

                n = input("Bist zu welchem n sollen die Regeln geprüft werden? "
                          f"{"".join([f"\n[{i + 1}] {subkat}"
                                      for (i, subkat) in enumerate(Q[Kategorie])])} \nchoice: ").replace(' ', '')

                if not n.isnumeric() or int(n) > len(Q[Kategorie]):
                    raise "Error, illegal input!!!"

                hypotheses = []
                count = 0

                number = 2*len(Q[Kategorie])*sum([bino(len(Q[Kategorie]), k) for k in range(1, int(n) + 1)])
                for k in range(1, int(n)+1):
                    for combination in it.combinations(Q[Kategorie], k):
                        for cat in Q[Kategorie]:
                            print(f"Hypotheses evaluated: {count+1}/{number}", end="\r")
                            count += 1
                            hypotheses.append(hypothesis_tester({'J': set(combination)}, {'L': {cat}}, {'J': J_dict_list, 'L': L_dict_list}))
                            print(f"Hypotheses evaluated: {count+1}/{number}", end="\r")
                            count += 1
                            hypotheses.append(hypothesis_tester({'L': set(combination)}, {'J': {cat}}, {'J': J_dict_list, 'L': L_dict_list}))

                print()
                q_value(hypotheses, number)

                hypotheses = [
                    hypothesis for hypothesis in hypotheses
                    if hypothesis["q_value"] <= 0.05 and hypothesis["n_antecedent"] >= 5
                ]

                hypotheses.sort(
                    key=lambda h: (
                        -h["leverage"],
                        -h["lift"],
                        -h["confidence"],
                        -h["support"],
                        -h["n_joint"],
                    )
                )

                print()
                anz = input("Wie viele der besten Hypothesen möchtest du sehen?: ")
                if not anz.isnumeric():
                    raise "Error, illegal input!!!"

                anz_2 = input("Wie viele Beispiel Publikationen möchtest du sehen pro beste Hypothese?: ")
                if not anz_2.isnumeric():
                    raise "Error, illegal input!!!"

                hypotheses = hypotheses[:int(anz)]
                for hypothesis in hypotheses:

                    set_ = [key for key in J_dict_list.keys()
                             if (set(hypothesis["antecedent"]['J']) <= set(J_dict_list[key].split(';'))
                                 and hypothesis["consequent"]['L'].intersection(set(L_dict_list[key].split(';')))) != set()] \
                             if list(hypothesis["antecedent"].keys())[0] == 'J' else \
                            [key for key in L_dict_list.keys()
                             if (set(hypothesis["antecedent"]['L']) <= set(L_dict_list[key].split(';'))
                                 and hypothesis["consequent"]['J'].intersection(set(J_dict_list[key].split(';'))))]

                    if not set_:
                        break

                    papes = np.random.choice(set_, int(anz_2), False)
                    hypothesis["example_papers"] = papes

                hypotheses.sort(
                    key=lambda h: (
                        -h["leverage"],
                        -h["lift"],
                        -h["confidence"],
                        -h["support"],
                        -h["n_joint"],
                    )
                )

                print()
                for hypothesis in hypotheses:
                    visualisation_number = max([len(ke) for ke in hypothesis.keys()]) + 1

                    print()
                    report.write("\n")
                    for ke in hypothesis.keys():
                        adjust_num = visualisation_number - len(ke)
                        adjust = "".join([" " for _ in range(adjust_num)])
                        entry = round(hypothesis[ke], 10) if str(hypothesis[ke]).isnumeric() else hypothesis[ke]
                        print(adjust + f"{ke}: {entry}")
                        report.write(adjust + f"{ke}: {entry}" + "\n")

            else:
                raise "Error, illegal input!!!"

    elif ana == 'a':
        with open(f"Analysis_Report.txt", "w", encoding="utf-8") as report:
            report.write(f"Report of <{Kategorien[Kategorie]}>.\n")

            ############################################################################################################
            # Krippendorf alpha

            print("\n\nKRIPPENDORF ALPHA")
            report.write("\n\nKRIPPENDORF ALPHA\n")

            set_func = ((lambda X, Y:
                        (set(X.split(';')).intersection(set(Y.split(';'))),
                         set(X.split(';')).union(set(Y.split(';'))))) if is_multichoice else
                        (lambda X_, Y_: ({X_}.intersection({Y_}), {X_}.union({Y_}))))

            corroboration = list_dictifier(Q, Kategorie)
            Do, count = ({measure:0 for measure in measures} if is_multichoice else 0,
                         {measure:1 for measure in measures} if is_multichoice else 1)
            J_bin, L_bin = [], []
            tracker = 0

            for key in J_dict_list.keys():
                if key in L_dict_list:

                    if Kategorie == 0:
                        tracker += 1

                        J_buffer, L_buffer = [], []
                        for sub_section in Q[0]:
                            J_buffer.append(1 if sub_section in {J_dict_list[key][0]} else 0)
                            L_buffer.append(1 if sub_section in {L_dict_list[key][0]} else 0)

                        J_bin.append(J_buffer)
                        L_bin.append(L_buffer)

                        if J_dict_list[key][0] == L_dict_list[key][0]:
                            if J_dict_list[key][0] == '1':
                                corroboration['1'] += 1
                            else:
                                corroboration['0'] += 1

                        Do = mean_update(Do, (1 if J_dict_list[key][0] !=
                                                   L_dict_list[key][0] else 0), count)
                        count += 1

                    elif J_dict_list[key][0] == L_dict_list[key][0] == '1':
                        sf = set_func(J_dict_list[key][Kategorie], L_dict_list[key][Kategorie])
                        tracker += 1

                        if is_multichoice:
                            bin_builder(Q[Kategorie], corroboration, sf, key, Kategorie, J_bin, L_bin, J_dict_list, L_dict_list)

                            for measure in measures:
                                Do[measure] = mean_update(Do[measure],
                                                          distance_measure(J_dict_list[key][Kategorie].split(';'),
                                                                      L_dict_list[key][Kategorie].split(';'),
                                                                      measure, len(Q[Kategorie])-1), count[measure])
                                count[measure] += 1

                        else:
                            bin_builder(Q[Kategorie], corroboration, sf, key, Kategorie, J_bin, L_bin, J_dict_list, L_dict_list)

                            Do = mean_update(Do, (1 if J_dict_list[key][Kategorie] !=
                                                       L_dict_list[key][Kategorie] else 0), count)
                            count += 1

            if is_multichoice:
                for measure in measures:
                    print(f"\nMeasure used: {measure} \n"
                    f"K_alpha = {alpha_formula(Do[measure], expected_distance(len(Q[Kategorie]), measure))}")
                    report.write(f"\nMeasure used: {measure} \n"
                    f"K_alpha = {alpha_formula(Do[measure], expected_distance(len(Q[Kategorie]), measure))}\n")

            else:
                print(f"K_alpha = {alpha_formula(Do, default_exp_dist(len(Q[Kategorie])))}")
                report.write(f"K_alpha = {alpha_formula(Do, default_exp_dist(len(Q[Kategorie])))}\n")

            ############################################################################################################
            # Corroboration

            print("\n\nCORROBORATION\n")
            report.write("\n\nCORROBORATION\n\n")

            sorting_func = lambda x: x[1]
            visualisation_number = max([len(sub) for sub in Q[Kategorie]]) + 1

            tran = lambda x: ("yes" if x == '1' else "no") if x in ['0', '1'] else x
            corroborations = []
            for key, value in corroboration.items():
                adjust_num = visualisation_number - len(key)
                adjust = "".join([" " for _ in range(adjust_num)])
                corroborations.append([key, value])
                print(adjust + f"{tran(key)}: {value}/{tracker} ({100*(value/tracker):.2f}%)")
                report.write(adjust + f"{tran(key)}: {value}/{tracker} ({100*(value/tracker):.2f}%)\n")

            corroborations.sort(key=sorting_func)

            toco = sum([corroborations[i][1] for i in range(len(corroborations))])
            total = tracker * len(corroborations)
            print(f"\nTotal corroboration: {toco}/{total} ({100 * (toco / total):.2f}%)\n")
            report.write(f"\nTotal corroboration: {toco}/{total} ({100 * (toco / total):.2f}%)\n\n")

            print("Points of least corroboration: ")
            report.write("Points of least corroboration: \n")
            for i in range(min(5, len(Q[Kategorie]))):
                print(f"Subcategory: {corroborations[i][0]}; Corroboration: {corroborations[i][1]} "
                      f"({100*corroborations[i][1]/tracker:.2f}%)")
                report.write(f"Subcategory: {corroborations[i][0]}; Corroboration: {corroborations[i][1]} "
                      f"({100*corroborations[i][1]/tracker:.2f}%)\n")

            ############################################################################################################
            # Correlation

            print("\n\nCORRELATION\n")
            report.write("\n\nCORRELATION\n\n")

            percentage = input("Would you like a phi correlation matrix or "
                               "a percentage correlation matrix? (options: phi, per): ").lower()

            if not percentage in ["phi", "per"]:
                raise "Error, illegal input!!!"

            J_bin, L_bin = np.array(J_bin), np.array(L_bin)

            correlations = correlator(J_bin, L_bin, percentage == "per")

            print("Same-option correlation between the coders: ")
            report.write("Same-option correlation between the coders: \n")
            print(str(correlations[0]) + "\n")
            report.write(str(correlations[0]) + "\n\n")


            print("Correlate every option of Julian with every option of Lukka: ")
            report.write("Correlate every option of Julian with every option of Lukka: \n")

            nan_label, fixed_matrix, fixed_labels_indices = [], [], []
            for (index, row) in enumerate(correlations[1]):
                is_nan = True
                for column in row:
                    if not np.isnan(column):
                        is_nan = False
                        fixed_matrix.append(correlations[1][index])
                        fixed_labels_indices.append(index)
                        break

                if is_nan:
                    nan_label.append(Q[Kategorie][index])

            remove = lambda arr, i: [entry for j, entry in enumerate(arr) if j in i]
            fixed_matrix = [remove(row, fixed_labels_indices) for row in fixed_matrix]

            print(f"\"nan\" labels: {nan_label}\n")
            report.write(f"\"nan\" labels: {nan_label}\n\n")

            print("Correlation of how many options each coder chooses: ")
            report.write("Correlation of how many options each coder chooses: \n")
            print(f"rho = {correlations[2][0]} \np = {correlations[2][1]} ")
            report.write(f"rho = {correlations[2][0]} \np = {correlations[2][1]} \n")

            if percentage == "per":
                combined_correlation_visualiser(matrix=np.array(fixed_matrix),
                                    labels=[tran(Q[Kategorie][index]) for index in fixed_labels_indices],
                                    y_label="Julian",
                                    x_label="Lukka",
                                    name_size=10,
                                    cut_off=0,
                                    bar_title="Percentage correlation",
                                    same_option_corr=[correlations[0][index] for index in fixed_labels_indices],
                                    A_counts=J_bin.sum(axis=1),
                                    B_counts=L_bin.sum(axis=1),
                                    rho=correlations[2][0],
                                    p=correlations[2][1])

            else:
                combined_correlation_visualiser(matrix=np.array(fixed_matrix),
                                    labels=[tran(Q[Kategorie][index]) for index in fixed_labels_indices],
                                    y_label="Julian",
                                    x_label="Lukka",
                                    name_size=10,
                                    cut_off=0.1,
                                    bar_title="Cross-coder correlation heatmap",
                                    min_val=-1,
                                    same_option_corr=[correlations[0][index] for index in fixed_labels_indices],
                                    A_counts=J_bin.sum(axis=1),
                                    B_counts=L_bin.sum(axis=1),
                                    rho=correlations[2][0],
                                    p=correlations[2][1])
    else:
        raise "Error, illegal input!!!"
