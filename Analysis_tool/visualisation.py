import matplotlib.pyplot as plt
import numpy as np


def combined_correlation_visualiser(
        matrix,
        same_option_corr,
        A_counts,
        B_counts,
        rho,
        p,
        labels,
        x_label="Coder B",
        y_label="Coder A",
        name_size=3,
        cut_off=0.09,
        min_val=0,
        max_val=1,
        title="Cross-coder selection probability heatmap",
        bar_title="Phi correlation"
):

    labels = [label[:name_size] for label in labels]

    # ---------------------------------------------------------
    # Figure layout
    #
    # Heatmap occupies the entire left side.
    # Same-option correlations are top-right.
    # Number-of-options relationship is bottom-right.
    # ---------------------------------------------------------

    fig = plt.figure(figsize=(10, 6))

    gs = fig.add_gridspec(
        2,
        2,
        width_ratios=[2, 1],
        height_ratios=[1, 1]
    )

    ax_matrix = fig.add_subplot(gs[:, 0])
    ax_same = fig.add_subplot(gs[0, 1])
    ax_counts = fig.add_subplot(gs[1, 1])


    # =========================================================
    # 1. CROSS-CODER MATRIX
    #
    # This is your original visualisation, unchanged apart from
    # using ax_matrix instead of creating its own figure.
    # =========================================================

    im = ax_matrix.imshow(
        matrix,
        vmin=min_val,
        vmax=max_val
    )

    cbar = plt.colorbar(
        im,
        ax=ax_matrix
    )

    cbar.set_label(bar_title)

    ax_matrix.set_xticks(range(len(labels)))
    ax_matrix.set_yticks(range(len(labels)))

    ax_matrix.set_xticklabels(
        labels,
        rotation=45,
        ha="right"
    )

    ax_matrix.set_yticklabels(labels)

    ax_matrix.set_xlabel(x_label)
    ax_matrix.set_ylabel(y_label)
    ax_matrix.set_title(title)

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):

            value = matrix[i, j]

            co = True

            if np.isnan(value):
                text = "NaN"
                color = "black"

            else:
                text = f"{value:.2f}"

                color = (
                    "white"
                    if abs(value) > 0.5
                    else "black"
                )

                co = abs(value) > cut_off

            if co:
                ax_matrix.text(
                    j,
                    i,
                    text,
                    ha="center",
                    va="center",
                    color=color
                )


    # =========================================================
    # 2. SAME-OPTION CORRELATION
    # =========================================================

    same_option_corr = np.asarray(same_option_corr)

    y = np.arange(len(labels))

    ax_same.barh(
        y,
        same_option_corr
    )

    ax_same.set_yticks(y)
    ax_same.set_yticklabels(labels)

    ax_same.set_xlim(-1, 1)
    ax_same.axvline(0)

    ax_same.set_xlabel("Phi correlation")
    ax_same.set_title("Same-option correlation")

    # Put numerical correlation next to each bar
    for i, value in enumerate(same_option_corr):

        if np.isnan(value):

            ax_same.text(
                0,
                i,
                "NaN",
                va="center",
                ha="center"
            )

        else:

            ax_same.text(
                value,
                i,
                f" {value:.2f}",
                va="center",
                ha="left" if value >= 0 else "right"
            )

    # Put first option at the top, like the matrix
    ax_same.invert_yaxis()


    # =========================================================
    # 3. CORRELATION OF NUMBER OF OPTIONS SELECTED
    # =========================================================

    A_counts = np.asarray(A_counts)
    B_counts = np.asarray(B_counts)

    # Many papers will have exactly the same (A_count, B_count)
    # combination, so collapse identical points and let point size
    # represent how many papers are there.
    pairs = np.column_stack(
        (A_counts, B_counts)
    )

    unique_pairs, frequencies = np.unique(
        pairs,
        axis=0,
        return_counts=True
    )

    ax_counts.scatter(
        unique_pairs[:, 1],
        unique_pairs[:, 0],
        s=frequencies * 35
    )

    max_count = int(
        max(
            np.max(A_counts),
            np.max(B_counts)
        )
    )

    # y = x reference line:
    # both coders chose the same number of options
    ax_counts.plot(
        [0, max_count],
        [0, max_count],
        linestyle="--"
    )

    ax_counts.set_xticks(
        range(max_count + 1)
    )

    ax_counts.set_yticks(
        range(max_count + 1)
    )

    ax_counts.set_xlabel(
        f"Options selected by {x_label}"
    )

    ax_counts.set_ylabel(
        f"Options selected by {y_label}"
    )

    ax_counts.set_title(
        "Number of options selected\n"
        f"Spearman ρ = {rho:.2f}, p = {p:.3g}"
    )


    # ---------------------------------------------------------
    # Final layout
    # ---------------------------------------------------------

    plt.tight_layout()
    plt.show()

