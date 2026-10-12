import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

// No adapter: this example runs with `vite dev`. Add one (adapter-node, for
// instance) if you want to deploy it.
export default {
  preprocess: vitePreprocess(),
  kit: {},
};
