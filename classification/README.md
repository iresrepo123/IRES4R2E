### Kendall's Tau-b Coefficient

**Kendall's Tau-b** ($\tau_b$) is a non-parametric statistic used to measure the ordinal association between two measured quantities. It is particularly suitable for evaluating the similarity of two rankings, especially when the data contains tied ranks.

#### Mathematical Definition

Given two variables $X$ and $Y$, each with $n$ observations, let:

- $n_c$ be the number of **concordant** pairs.
- $n_d$ be the number of **discordant** pairs.
- $n_x$ be the number of pairs tied **only** on $X$ (i.e., $X_i = X_j$ but $Y_i \neq Y_j$).
- $n_y$ be the number of pairs tied **only** on $Y$ (i.e $Y_i = Y_j$ but $X_i \neq X_j$).

The Kendall's Tau-b coefficient is defined as:

$$ \tau_b = \frac{n_c - n_d}{\sqrt{(n_c + n_d + n_x)(n_c + n_d + n_y)}} $$

#### Interpretation of Pairs

For any two distinct observations $(X_i, Y_i)$ and $(X_j, Y_j)$ where $i < j$:

- **Concordant**: The ranks agree in direction. That is, $(X_i - X_j)(Y_i - Y_j) > 0$.
- **Discordant**: The ranks disagree in direction. That is, $(X_i - X_j)(Y_i - Y_j) < 0$.
- **Tied**: The observations share the same rank in at least one variable. That is, $(X_i - X_j)(Y_i - Y_j) = 0$.

#### Value Range and Properties

- Range

  : $\tau_b \in [-1, +1]$.

  - $\tau_b = +1$ indicates perfect agreement in ranking.
  - $\tau_b = -1$ indicates perfect disagreement (inverse ranking).
  - $\tau_b = 0$ suggests no ordinal association.

- **Handling Ties**: Unlike Kendall's Tau-a, the denominator of $\tau_b$ includes a correction factor for ties ($\sqrt{\dots}$). This ensures that the coefficient reaches the theoretical maximum of $+1$ or minimum of $-1$ even when tied ranks are present, making it the preferred variant for ranking similarity evaluation.

------

*Note: When citing this in your paper, you may also want to include the original reference: Kendall, M. G. (1938). A new measure of rank correlation. Biometrika, 30(1/2), 81-93.*
