# Calix 0.1.13

- Calculation cells return each top-level newline-separated expression in order. A trailing semicolon suppresses that line's output. Lines inside brackets remain part of the same expression. A line ending in an operator continues on the next line; a new line starting with `+` or `-` starts a separate signed expression.
- Explicit numerical demonstrations contain ten expressions: one elementary calculation, high precision, trigonometry, complex arithmetic, combinatorics, sums, products, special functions, a matrix operation and a determinant. Repeated clicks select different expressions in every category.
- Unit conversion and unit arithmetic share one demonstration, with three variants of ten expressions. Compound units use slash notation, including parentheses around multiple denominator factors. Numeric fractions retain fraction formatting.
- Basic demonstrations use separate expressions without `Column`. The `Column` function remains supported for existing notebooks.
- Complete case notebooks sort by the displayed title: pinyin in Chinese, alphabetical order in English. Sorting updates immediately when the interface language changes.
- The Windows x64 installer includes the calculation service, native C++ solver and third-party notices. No separate Python or Node.js installation is required.
