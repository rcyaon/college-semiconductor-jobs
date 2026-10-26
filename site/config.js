// Settings for the optional "Sign in with GitHub" button on the website.
//
// Leave both blank and the site still works: applications are saved in the
// browser, and "Sync with GitHub" falls back to pasting a personal access token.
//
// To turn on one-click GitHub sign-in, follow "Optional: GitHub sign-in" in the README
// and fill these in.
window.SEMI_JOBS_CONFIG = {
  githubClientId: "",    // Client ID of your GitHub OAuth App
  tokenExchangeUrl: "",  // URL of the deployed worker/github-oauth.js, e.g. https://semi-jobs-oauth.you.workers.dev
};
