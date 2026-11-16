
def disjoint_distance(A, B):
    if not set(A).isdisjoint(set(B)):
        return 0
    return 1

def disjoint_exp_dist(n):
    return ((3**(n-1))-1) / (4**(n-1))

def subset_distance(A, B):
    if set(A) <= set(B) or set(A) >= set(B):
        return 0
    return 1

def subset_exp_dist(n):
    return ((4**(n-1))+3*(2**(n-1))-2*(3**(n-1))-2) / (4**(n-1))

def jaccard(A, B):
    diff = set(A).symmetric_difference(set(B))
    union = set(A).union(set(B))
    return len(diff) / len(union)

def jaccard_exp_dist(n):
    return (2/3)*(1-(1/(4**(n-1))))

def relative_subset(A, B, n):
    return 1 - (len(set(A).intersection(set(B)))/min(len(set(A)), len(set(B))))*(1 - abs(len(set(A)) - len(set(B)))/(n-1))

def relative_subset_exp_dist(n):
    return ((2*n-1)/(4*(n-1))) + ((n-2)/((n-1)*(2**n))) - (1/(4**(n-1)))

def default_exp_dist(n):
    return 1 - (1 / n)

def distance_measure(A, B, type_, n=None):
    return disjoint_distance(A, B) if type_ == "disjoint" else (
               subset_distance(A, B) if type_ == "subset" else (
               jaccard(A, B) if type_ == "jaccard" else
               relative_subset(A, B, n) if type_ == "relative_subset" else None))

def expected_distance(n, type_):
    return disjoint_exp_dist(n) if type_ == "disjoint" else (
               subset_exp_dist(n) if type_ == "subset" else (
               jaccard_exp_dist(n) if type_ == "jaccard" else
               relative_subset_exp_dist(n) if type_ == "relative_subset" else None))
