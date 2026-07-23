# Contributing to Aesthetics-KG

Thank you for your interest in contributing to **Aesthetics-KG**! This project is a living knowledge graph of internet aesthetics — your contributions help it stay accurate, comprehensive, and useful for researchers, developers, and curious people alike.

Please read through these guidelines before opening an issue or pull request.

---

## 1. Ways to Contribute

| Contribution | How? |
|:---|:---|
| **Report a data bug** | If you find incorrect, missing, or inconsistent data (wrong relations, mislabelled entities, broken URIs), please open a [GitHub Issue](https://github.com/dersuchendee/aesthetics-kg/issues) using the **Bug Report** template. Include the affected aesthetic name, the incorrect triple or property, and what the correct value should be. |
| **Request a new aesthetic or property** | If an aesthetic is missing from the graph, or you think a new ontology property would improve coverage, open a [Feature Request](https://github.com/dersuchendee/aesthetics-kg/issues) issue. Describe the aesthetic, link to its Aesthetics Wiki page if available, and explain what cultural or relational information it would add. |
| **Request a website feature** | If you have an idea for the [interactive explorer](https://dersuchendee.github.io/aesthetics-kg/) — a new view, filter, visualisation, or interaction — open a [Feature Request](https://github.com/dersuchendee/aesthetics-kg/issues) issue describing what you'd like and why it would be useful. |
| **Improve documentation** | If something in the README, the SPARQL query files, or the ontology documentation is unclear or out of date, feel free to open an issue or submit a pull request directly with your proposed change. |
| **Improve SPARQL competency questions** | The `requirements/` folder contains user stories and SPARQL implementations. If a query is wrong, incomplete, or could be improved, open a PR with the corrected query. Always test against the live endpoint before submitting. |
| **Extend the build pipeline** | The `code/` folder contains the RML mapping and build scripts. If you'd like to add a new data source, mapping rule, or reconciliation script, please open an issue first to discuss the approach. |

---

## 2. Reporting Bugs

When reporting a data or query bug, please include:

- **Affected entity** — the aesthetic name and its URI (e.g., `https://w3id.org/aesthetics-kg/resource/aesthetic/dark-academia`)
- **What is wrong** — the incorrect triple, property value, or query result
- **What it should be** — the expected correct value, with a source if possible (e.g., link to Aesthetics Wiki, Wikidata, or a publication)
- **How to reproduce** — steps to see the issue on the [explorer](https://dersuchendee.github.io/aesthetics-kg/) or the [SPARQL endpoint](https://semantics.istc.cnr.it/aesthetics-kg/query/)

---

## 3. Commit Guidelines

Keep commits small and focused — one logical change per commit.

Use the imperative mood in commit messages (e.g., `Add missing motifs for Goblincore`) and keep the subject under 60 characters.

You may optionally use these emoji codes:

| Code | Emoji | Use for |
|:---|:---:|:---|
| `:bug:` | 🐛 | Fix incorrect data or a broken query |
| `:sparkles:` | ✨ | Add a new aesthetic, property, or feature |
| `:memo:` | 📝 | Add or update documentation |
| `:recycle:` | ♻️ | Refactor mapping rules or pipeline scripts |
| `:adhesive_bandage:` | 🩹 | Minor fix (typo, label correction) |
| `:test_tube:` | 🧪 | Add or update SPARQL competency questions |

---

## 4. Submitting a Pull Request

1. Fork the [aesthetics-kg repository](https://github.com/dersuchendee/aesthetics-kg)
2. Clone your fork:
```bash
git clone git@github.com:YOUR_USERNAME/aesthetics-kg.git
cd aesthetics-kg
```
3. Create a branch:
```bash
git switch -c your-branch-name
```
4. Make your changes, then commit:
```bash
git add <specific-files>
git commit -m "your commit message"
git push origin your-branch-name
```
5. Open a pull request to the `main` branch with a clear description of what changed and why
6. If your PR modifies SPARQL queries, confirm they work against the live endpoint at `https://semantics.istc.cnr.it/aesthetics-kg/graphdb/repositories/aesthetics`
7. Be responsive to review feedback

---

## 5. Code of Conduct

Be respectful and constructive. This is a research project with contributors from different backgrounds. We welcome questions, corrections, and new ideas — as long as they're shared kindly.

---

By contributing, you agree that your contributions will be licensed under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) (data) or [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) (code), consistent with the existing project licenses.

We look forward to your contributions!
