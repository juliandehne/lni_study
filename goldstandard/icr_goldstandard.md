# Goldstandard Intercoder Reliability (alice vs lukka)

Research-software gate: 80 papers confirmed by both coders (ICR computed over these); 18 vetoed by one coder; gate agreement 0.846 over 117 jointly-decided papers.

## Per dimension (multi-value cells as sets)

| dimension          |   n_shared |   raw_agreement |   krippendorff_alpha |   cohen_kappa |
|:-------------------|-----------:|----------------:|---------------------:|--------------:|
| research_position  |         79 |           0.557 |                0.371 |         0.37  |
| software_lifecycle |         78 |           0.282 |                0.205 |         0.209 |
| software_type      |         78 |           0.423 |                0.39  |         0.392 |
| techstack          |         77 |           0.636 |                0.577 |         0.575 |
| evaluation         |         78 |           0.321 |                0.274 |         0.277 |

## Multi-value dimensions, one binary variable per subcategory

Each subcategory is scored as present/absent, so partial overlap is priced fairly and the disagreement is localised to the category. `positive_agreement` is the specific agreement on presence (2*both / (a+b)), which stays informative for rare categories, where the shared absences that dominate raw agreement carry no information. Macro averages weigh every subcategory equally.

| dimension          |   n_categories |   mean_alpha |   mean_kappa |   mean_positive_agreement |   mean_jaccard |   mean_dice |   exact_set_match |
|:-------------------|---------------:|-------------:|-------------:|--------------------------:|---------------:|------------:|------------------:|
| evaluation         |              9 |        0.469 |        0.475 |                     0.55  |          0.525 |       0.598 |             0.321 |
| software_lifecycle |              6 |        0.356 |        0.372 |                     0.745 |          0.721 |       0.813 |             0.282 |
| software_type      |             13 |        0.509 |        0.512 |                     0.55  |          0.639 |       0.712 |             0.423 |
| techstack          |             15 |        0.748 |        0.748 |                     0.771 |          0.739 |       0.767 |             0.636 |

### Per subcategory

| dimension          | category                       | in_schema   |   n_shared |   n_a |   n_b |   n_both |   prevalence |   raw_agreement |   positive_agreement |   jaccard |   krippendorff_alpha |   cohen_kappa |
|:-------------------|:-------------------------------|:------------|-----------:|------:|------:|---------:|-------------:|----------------:|---------------------:|----------:|---------------------:|--------------:|
| software_lifecycle | anforderungen                  | True        |         78 |    29 |    33 |       23 |        0.397 |           0.795 |                0.742 |     0.59  |                0.574 |         0.573 |
| software_lifecycle | deployment_betrieb             | True        |         78 |    18 |    10 |        7 |        0.179 |           0.821 |                0.5   |     0.333 |                0.395 |         0.401 |
| software_lifecycle | entwurf                        | True        |         78 |    71 |    67 |       65 |        0.885 |           0.897 |                0.942 |     0.89  |                0.501 |         0.501 |
| software_lifecycle | implementierung                | True        |         78 |    78 |    73 |       73 |        0.968 |           0.936 |                0.967 |     0.936 |               -0.026 |         0     |
| software_lifecycle | projektdefinition              | True        |         78 |    39 |    45 |       34 |        0.538 |           0.795 |                0.81  |     0.68  |                0.59  |         0.59  |
| software_lifecycle | testen_qualitaetssicherung     | True        |         78 |    24 |    47 |       18 |        0.455 |           0.551 |                0.507 |     0.34  |                0.101 |         0.168 |
| software_type      | analysis_pipeline              | True        |         78 |     6 |    20 |        6 |        0.167 |           0.821 |                0.462 |     0.3   |                0.358 |         0.389 |
| software_type      | domain_specific_language       | True        |         78 |     6 |     6 |        5 |        0.077 |           0.974 |                0.833 |     0.714 |                0.821 |         0.819 |
| software_type      | embedded_hardware              | True        |         78 |     4 |     4 |        3 |        0.051 |           0.974 |                0.75  |     0.6   |                0.738 |         0.736 |
| software_type      | full_stack_application         | True        |         78 |    24 |    32 |       22 |        0.359 |           0.846 |                0.786 |     0.647 |                0.668 |         0.669 |
| software_type      | insufficient_information       | False       |         78 |     2 |     0 |        0 |        0.013 |           0.974 |                0     |     0     |               -0.006 |         0     |
| software_type      | library_package                | True        |         78 |    11 |     7 |        3 |        0.115 |           0.846 |                0.333 |     0.2   |                0.251 |         0.251 |
| software_type      | middleware_service             | True        |         78 |    24 |    32 |       23 |        0.359 |           0.872 |                0.821 |     0.697 |                0.723 |         0.725 |
| software_type      | ml_model                       | True        |         78 |     3 |     5 |        3 |        0.051 |           0.974 |                0.75  |     0.6   |                0.738 |         0.737 |
| software_type      | numerical_mathematical         | True        |         78 |    11 |    14 |        9 |        0.16  |           0.91  |                0.72  |     0.562 |                0.669 |         0.667 |
| software_type      | plugin_extension               | True        |         78 |    12 |     8 |        7 |        0.128 |           0.923 |                0.7   |     0.538 |                0.658 |         0.658 |
| software_type      | script                         | True        |         78 |     2 |     0 |        0 |        0.013 |           0.974 |                0     |     0     |               -0.006 |         0     |
| software_type      | test_automation_framework      | False       |         78 |     1 |     0 |        0 |        0.006 |           0.987 |                0     |     0     |                0     |         0     |
| software_type      | vr_application                 | True        |         78 |     3 |     3 |        3 |        0.038 |           1     |                1     |     1     |                1     |         1     |
| techstack          | ada                            | True        |         77 |     1 |     1 |        1 |        0.013 |           1     |                1     |     1     |                1     |         1     |
| techstack          | c_cpp                          | True        |         77 |    10 |    10 |        8 |        0.13  |           0.948 |                0.8   |     0.667 |                0.772 |         0.77  |
| techstack          | csharp_dotnet                  | True        |         77 |     3 |     3 |        3 |        0.039 |           1     |                1     |     1     |                1     |         1     |
| techstack          | formal_specification_languages | True        |         77 |     2 |     1 |        0 |        0.019 |           0.961 |                0     |     0     |               -0.013 |        -0.018 |
| techstack          | go                             | True        |         77 |     1 |     1 |        1 |        0.013 |           1     |                1     |     1     |                1     |         1     |
| techstack          | hpc_parallel_computing         | True        |         77 |     3 |     0 |        0 |        0.019 |           0.961 |                0     |     0     |               -0.013 |         0     |
| techstack          | insufficient_information       | False       |         77 |    26 |    28 |       20 |        0.351 |           0.818 |                0.741 |     0.588 |                0.603 |         0.601 |
| techstack          | java_jvm                       | True        |         77 |    17 |    16 |       14 |        0.214 |           0.935 |                0.848 |     0.737 |                0.808 |         0.807 |
| techstack          | javascript_web                 | True        |         77 |     6 |     4 |        3 |        0.065 |           0.948 |                0.6   |     0.429 |                0.575 |         0.573 |
| techstack          | php                            | False       |         77 |     3 |     3 |        3 |        0.039 |           1     |                1     |     1     |                1     |         1     |
| techstack          | python                         | True        |         77 |     6 |     7 |        6 |        0.084 |           0.987 |                0.923 |     0.857 |                0.917 |         0.916 |
| techstack          | r_lang                         | True        |         77 |     2 |     2 |        2 |        0.026 |           1     |                1     |     1     |                1     |         1     |
| techstack          | sql_db                         | True        |         77 |    14 |    11 |       11 |        0.162 |           0.961 |                0.88  |     0.786 |                0.858 |         0.857 |
| techstack          | visual_basic                   | True        |         77 |     2 |     2 |        2 |        0.026 |           1     |                1     |     1     |                1     |         1     |
| techstack          | xml_xsd                        | True        |         77 |    15 |    16 |       12 |        0.201 |           0.909 |                0.774 |     0.632 |                0.719 |         0.717 |
| evaluation         | alternatives_comparison        | True        |         78 |     3 |    11 |        1 |        0.09  |           0.846 |                0.143 |     0.077 |                0.064 |         0.088 |
| evaluation         | benchmarking                   | True        |         78 |    11 |    21 |        9 |        0.205 |           0.821 |                0.562 |     0.391 |                0.453 |         0.463 |
| evaluation         | conceptual_evaluation          | True        |         78 |    17 |    17 |       11 |        0.218 |           0.846 |                0.647 |     0.478 |                0.552 |         0.549 |
| evaluation         | empirical_study                | True        |         78 |    10 |    18 |        8 |        0.179 |           0.846 |                0.571 |     0.4   |                0.481 |         0.487 |
| evaluation         | insufficient_information       | False       |         78 |     8 |     2 |        2 |        0.064 |           0.923 |                0.4   |     0.25  |                0.363 |         0.374 |
| evaluation         | performance_evaluation         | True        |         78 |    22 |    26 |       18 |        0.308 |           0.846 |                0.75  |     0.6   |                0.641 |         0.64  |
| evaluation         | planned                        | True        |         78 |    14 |    10 |       10 |        0.154 |           0.949 |                0.833 |     0.714 |                0.804 |         0.804 |
| evaluation         | testing                        | True        |         78 |    14 |    24 |        9 |        0.244 |           0.744 |                0.474 |     0.31  |                0.309 |         0.319 |
| evaluation         | usability_study                | True        |         78 |     2 |     5 |        2 |        0.045 |           0.962 |                0.571 |     0.4   |                0.554 |         0.555 |
