import js from "@eslint/js"
import pluginVue from "eslint-plugin-vue"
import tseslint from "typescript-eslint"

// Flat config (ESLint 9+). `eslint` and `eslint-plugin-vue` were already installed with no
// config file at all — `npm run lint` failed outright with "couldn't find a configuration
// file," so nothing here was ever actually linted, locally or in CI. `@eslint/js` and
// `typescript-eslint` are added as devDependencies alongside this file (run `npm install`)
// since a `.ts`-aware config needs a TS-aware parser, not just the base JS one.
export default [
  // vite-env.d.ts is Vite's own generated .vue-module boilerplate, not app code — its `{}` type
  // in DefineComponent<{}, {}, unknown> is a known, harmless pattern in every Vite+Vue+TS
  // project, not a real bug to fix here.
  { ignores: ["dist/**", "node_modules/**", "**/*.d.ts"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  // "flat/essential" (correctness rules only), not "flat/recommended" — recommended also turns on
  // eslint-plugin-vue's stylistic/formatting rules (one-attribute-per-line, forced line breaks
  // inside <td>/<th>/<option>, etc.), which fight this codebase's established single-line-tag
  // style throughout and would drown real findings under ~1,300 pure style warnings.
  ...pluginVue.configs["flat/essential"],
  {
    files: ["**/*.vue"],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },
  {
    rules: {
      // Several single-word view/store names already exist (e.g. App.vue) and renaming them is
      // out of scope for turning the linter on.
      "vue/multi-word-component-names": "off",
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
]
