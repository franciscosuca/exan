## [1.7.5](https://github.com/franciscosuca/exan/compare/v1.7.4...v1.7.5) (2026-09-07)

### Bug Fixes

* **add CMD instruction to Dockerfile for nginx:** fix: add CMD instruction to Dockerfile for nginx ([347ca6d](https://github.com/franciscosuca/exan/commit/347ca6d2da0978cba1ca752fe3d140b37c3ad557))

## [1.7.4](https://github.com/franciscosuca/exan/compare/v1.7.3...v1.7.4) (2026-09-07)

### Bug Fixes

* **add GCP_RUN_SERVICE_ACCOUNT to deployment documentation and Terraform configuration:** fix: add GCP_RUN_SERVICE_ACCOUNT to deployment documentation and Terraform configuration ([bae0b2e](https://github.com/franciscosuca/exan/commit/bae0b2ee0338abf8d8fa61a2e128eb3726858c45))
* **add service account to Cloud Run deployment steps:** fix: add service account to Cloud Run deployment steps ([c886da2](https://github.com/franciscosuca/exan/commit/c886da2f41fc08bc9bbf5525235c6e9c45c02bd7))
* **update service account variable for Cloud Run deployment:** fix: update service account variable for Cloud Run deployment ([96e06ce](https://github.com/franciscosuca/exan/commit/96e06ce663c18b7bba2d3b3b33f279a15c1e93a2))

## [1.7.3](https://github.com/franciscosuca/exan/compare/v1.7.2...v1.7.3) (2026-09-06)

### Bug Fixes

* **remove unnecessary environment variable PORT from Cloud Run deployment:** fix: remove unnecessary environment variable PORT from Cloud Run deployment ([a46cf08](https://github.com/franciscosuca/exan/commit/a46cf084175a4a1aa1498ad3e0ed274a4f8749fe))

## [1.7.2](https://github.com/franciscosuca/exan/compare/v1.7.1...v1.7.2) (2026-08-31)

### Bug Fixes

* **restrict preflight workflow permissions:** fix: restrict preflight workflow permissions ([a7f8a0e](https://github.com/franciscosuca/exan/commit/a7f8a0ed49cff92e27453d17b708fc59f2f33867))
* **skip cloud deployment without GCP credentials:** fix: skip cloud deployment without GCP credentials ([f864513](https://github.com/franciscosuca/exan/commit/f8645136c5e741b3fd29cdd70208c9b45d0976a3))

## [1.7.1](https://github.com/franciscosuca/exan/compare/v1.7.0...v1.7.1) (2026-08-31)

### Bug Fixes

* **remove credentials_json from Cloud Run deployment workflow:** fix: remove credentials_json from Cloud Run deployment workflow ([e7d4e57](https://github.com/franciscosuca/exan/commit/e7d4e57467672fb490512527893300cc2a220269))
* **remove test job from Cloud Run deployment workflow:** fix: remove test job from Cloud Run deployment workflow ([d3a73a3](https://github.com/franciscosuca/exan/commit/d3a73a38f8630d7af03b20442f9d2661ded02eea))
* **set PROJECT_ID to a fixed value in Cloud Run deployment workflow:** fix: set PROJECT_ID to a fixed value in Cloud Run deployment workflow ([8b24b57](https://github.com/franciscosuca/exan/commit/8b24b57360d3400c4f78806bb408cdf9dab8c5c5))
* **update Cloud Run deployment secrets to remove unused keys:** fix: update Cloud Run deployment secrets to remove unused keys ([5f51ac3](https://github.com/franciscosuca/exan/commit/5f51ac32cf36320a0a0aa16fbe4cbc53db474360))
* **update Cloud Run deployment workflow to resolve backend URLs and streamline configuration:** fix: update Cloud Run deployment workflow to resolve backend URLs and streamline configuration ([1f14608](https://github.com/franciscosuca/exan/commit/1f14608a1ec1dedb8c790e058975eeb7eddb0b51))

## [1.7.0](https://github.com/franciscosuca/exan/compare/v1.6.1...v1.7.0) (2026-08-29)

### Features

* **add Cloud Run services and IAM configurations for auth-server, inference, and webapp:** feat: add Cloud Run services and IAM configurations for auth-server, inference, and webapp ([cb0e144](https://github.com/franciscosuca/exan/commit/cb0e14476f63f21de7edf6ffa719cf9a093b5f85))
* **add GitHub Actions workflows for deploying to Google Cloud Run and Cloud Build pipeline for multi-service deployment:** feat: add GitHub Actions workflows for deploying to Google Cloud Run and Cloud Build pipeline for multi-service deployment ([3bf87a6](https://github.com/franciscosuca/exan/commit/3bf87a6888cfc7ff854073b41560ba6e32a10ed8))
* **add outputs for webapp, auth-server, inference service, and artifact registry:** feat: add outputs for webapp, auth-server, inference service, and artifact registry ([2997ee6](https://github.com/franciscosuca/exan/commit/2997ee6c84a89795e5ce30a7589f9152451b8586))
* **implement file size validation for uploads and add corresponding tests:** feat: implement file size validation for uploads and add corresponding tests ([6a12c6c](https://github.com/franciscosuca/exan/commit/6a12c6c5fb6aaf280aaa51bea3ac38724643b81c))
* **update Cloud Run configurations and Terraform settings for improved resource management:** feat: update Cloud Run configurations and Terraform settings for improved resource management ([ad2d56d](https://github.com/franciscosuca/exan/commit/ad2d56d9fb0bdc1b6bbc64464fd135b95f59a9e5))

### Bug Fixes

* **correct Google Gemini API Key storage command in secrets setup:** fix: correct Google Gemini API Key storage command in secrets setup ([676dd2a](https://github.com/franciscosuca/exan/commit/676dd2ab37d70ef6bb00e426097b2d353c6db5fd))
* **refine response style guidelines for coding tasks and user interactions:** fix: refine response style guidelines for coding tasks and user interactions ([d92db59](https://github.com/franciscosuca/exan/commit/d92db596b48c39d50610d1e81826ce318434980d))
* **streamline secret version addition commands and clarify AI provider key setup:** fix: streamline secret version addition commands and clarify AI provider key setup ([5cf6430](https://github.com/franciscosuca/exan/commit/5cf64303493cce33f893bc562af9b4443688093c))
* **update GCP project ID and region in deployment documentation and Terraform variables:** fix: update GCP project ID and region in deployment documentation and Terraform variables ([7acd7b9](https://github.com/franciscosuca/exan/commit/7acd7b94c1b9c3c4c27c26fc76eab6b4c65c9c32))
* **update GCP region from us-central1 to europe-west1 in deployment setup:** fix: update GCP region from us-central1 to europe-west1 in deployment setup ([bcc0b55](https://github.com/franciscosuca/exan/commit/bcc0b550e1e9fa17aa72b9e119eb8172b257dd51))
* **update project_id description for clarity in Terraform variables:** fix: update project_id description for clarity in Terraform variables ([54e6423](https://github.com/franciscosuca/exan/commit/54e64233e83915f28f712f8abbe72b1efb0f9e98))
* **update Terraform state bucket name for consistency and add version configuration:** fix: update Terraform state bucket name for consistency and add version configuration ([ae7fe67](https://github.com/franciscosuca/exan/commit/ae7fe67ed57e2f631166e66a85f9cf2265ba6dd2))
* **update Terraform state bucket naming and service account creation for consistency:** fix: update Terraform state bucket naming and service account creation for consistency ([15a48fc](https://github.com/franciscosuca/exan/commit/15a48fcfd459bed56345b2888409d974a5ff3722))

## [1.6.1](https://github.com/franciscosuca/exan/compare/v1.6.0...v1.6.1) (2026-08-11)

## [1.6.0](https://github.com/franciscosuca/exan/compare/v1.5.2...v1.6.0) (2026-08-10)

### Features

* **add structured grammar feedback plan and evaluation results logging:** feat: add structured grammar feedback plan and evaluation results logging ([d8af7b4](https://github.com/franciscosuca/exan/commit/d8af7b44c40ddfa4e8d78be3e629db9dc9c3cafc))
* **Enhance grammar evaluation with structured feedback.:** feat: Enhance grammar evaluation with structured feedback. ([6279b17](https://github.com/franciscosuca/exan/commit/6279b176277cf0b4e4938919f8998e56b4c43a29))
* **enhance grammar findings and summary language:** feat: enhance grammar findings and summary language ([90f35f1](https://github.com/franciscosuca/exan/commit/90f35f105889f4980cdb6b92c70d5a4503999c2b))
* **Integrate Gemini model selection into provider workflows and enable user to modify or add key answers if necessary.:** feat: Integrate Gemini model selection into provider workflows and enable user to modify or add key answers if necessary. ([8882c0b](https://github.com/franciscosuca/exan/commit/8882c0b68a04080feaf580787bfd6c48295de66f))
* **migrate to structured grammar evaluation and remove legacy scoring:** feat: migrate to structured grammar evaluation and remove legacy scoring ([274f4be](https://github.com/franciscosuca/exan/commit/274f4be2e27ab7f2fa73436c459434810527fd77))

### Bug Fixes

* **add logs directory to .gitignore:** fix: add logs directory to .gitignore ([eb4cd5d](https://github.com/franciscosuca/exan/commit/eb4cd5d4256dc193084c9949489095eb7cc4c28f))
* **normalize batch provider feedback:** fix: normalize batch provider feedback ([2e60018](https://github.com/franciscosuca/exan/commit/2e600187418787d84631f05bd14d989c9429e8b5))
* **remove grammar grading percentages:** fix: remove grammar grading percentages ([263c790](https://github.com/franciscosuca/exan/commit/263c7900af2401c4c4f7e6c4ee8262b82bd241e6))
* **structure batch evaluation feedback:** fix: structure batch evaluation feedback ([9538825](https://github.com/franciscosuca/exan/commit/9538825bee11ad60907d556ee2f5d2e815b945e9))
* **update question number type to support alphanumeric values in models and API:** fix: update question number type to support alphanumeric values in models and API ([bd64b9c](https://github.com/franciscosuca/exan/commit/bd64b9c6b9064f24fd32cab467771e0c3bc6e734))

## [1.5.2](https://github.com/franciscosuca/exan/compare/v1.5.1...v1.5.2) (2026-08-05)

### Bug Fixes

* **remove stray inference startup expression:** fix: remove stray inference startup expression ([d1c65db](https://github.com/franciscosuca/exan/commit/d1c65db3dd5f00490aadb3265377ce53ef4aeeab))

## [1.5.1](https://github.com/franciscosuca/exan/compare/v1.5.0...v1.5.1) (2026-08-05)

## [1.5.0](https://github.com/franciscosuca/exan/compare/v1.4.1...v1.5.0) (2026-08-03)

### Features

* **persist inference run logs:** feat: persist inference run logs ([f8bbd24](https://github.com/franciscosuca/exan/commit/f8bbd24598ec077007a08e076361011bb37ad5c0))

### Bug Fixes

* **capture per-call provider usage:** fix: capture per-call provider usage ([1c9f753](https://github.com/franciscosuca/exan/commit/1c9f7538dcbec8e88ac48204a3fbf2b204b280b5))
* **keep logging failures from breaking requests:** fix: keep logging failures from breaking requests ([c531ad6](https://github.com/franciscosuca/exan/commit/c531ad65433a432d703d4707a9de15de7d1bca9f))
* **persist container logs at root path:** fix: persist container logs at root path ([dd2f3be](https://github.com/franciscosuca/exan/commit/dd2f3bea8d32ec51bdb402750db4c9e60165620d))

## [1.4.1](https://github.com/franciscosuca/exan/compare/v1.4.0...v1.4.1) (2026-08-02)

## [1.4.0](https://github.com/franciscosuca/exan/compare/v1.3.1...v1.4.0) (2026-07-31)

### Features

* **add German/English language selector with persistence:** feat(webapp): add German/English language selector with persistence ([1166104](https://github.com/franciscosuca/exan/commit/11661045385b425f394810c20bee0af3378c6fcc))
* **update authentication flow and proxy configuration for improved routing:** feat: update authentication flow and proxy configuration for improved routing ([d1fe564](https://github.com/franciscosuca/exan/commit/d1fe564ff6aabb08344e33160e46c83e465bad1e))

## [1.3.1](https://github.com/franciscosuca/exan/compare/v1.3.0...v1.3.1) (2026-07-29)

### Performance Improvements

* **update TypeScript and TSX versions to 7.0.2 and 4.23.1 respectively:** perf: update TypeScript and TSX versions to 7.0.2 and 4.23.1 respectively ([55c0041](https://github.com/franciscosuca/exan/commit/55c004104fb32555b1f80cfd3acba73bcd4a1eb5))

## [1.3.0](https://github.com/franciscosuca/exan/compare/v1.2.0...v1.3.0) (2026-07-28)

### Features

* **implement authentication flow with login and registration pages:** feat: implement authentication flow with login and registration pages ([ee45a0e](https://github.com/franciscosuca/exan/commit/ee45a0ecf98e219682e21fd93caabe64591f66d6))
* **implement authentication system with JWT and MongoDB:** feat: implement authentication system with JWT and MongoDB ([67ad3f9](https://github.com/franciscosuca/exan/commit/67ad3f9f406b869930ee5986cfbdbf48c361d9f3))

## [1.2.0](https://github.com/franciscosuca/exan/compare/v1.1.0...v1.2.0) (2026-07-25)

### Features

* **add batch exam evaluation mode and architecture diagrams:** feat: add batch exam evaluation mode and architecture diagrams ([871f430](https://github.com/franciscosuca/exan/commit/871f430b1474d5a74d8a0e62a7c2a0ad5dbe6921))

### Bug Fixes

* **resolve backend lint failures in prompt templates:** fix: resolve backend lint failures in prompt templates ([fc40046](https://github.com/franciscosuca/exan/commit/fc40046c7c6ac3d339f1b5b47bc534edebfb06eb))

## [1.1.0](https://github.com/franciscosuca/exan/compare/v1.0.0...v1.1.0) (2026-07-04)

### Features

* **add batch exam evaluation mode and architecture diagrams:** feat: add batch exam evaluation mode and architecture diagrams ([995dd70](https://github.com/franciscosuca/exan/commit/995dd70b9b9bc636d895b6d82ca725ebc3d438c3))

## 1.0.0 (2026-07-02)

### ⚠ BREAKING CHANGES

* Complete project restructure from template repository to AI exam scanning application.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>

### Features

* **Add agents, instructions and skills:** feat: Add agents, instructions and skills ([6e81c40](https://github.com/franciscosuca/exan/commit/6e81c40baaf0f3241e0d7e521dd31722346add78))
* transform into AI exam scanner application ([279e6b8](https://github.com/franciscosuca/exan/commit/279e6b80c2cc11d062e8299c79f0b205d78ff17d))

### Bug Fixes

* **resolve ruff lint errors in backend (E501, F401, I001):** fix: resolve ruff lint errors in backend (E501, F401, I001) ([53b067f](https://github.com/franciscosuca/exan/commit/53b067f1067c574e69d8754c3fe88abaa7a32e4b))
* **run npm steps from frontend in release workflow:** fix(ci): run npm steps from frontend in release workflow ([6dfd25f](https://github.com/franciscosuca/exan/commit/6dfd25faa85e76aeda86becca2d1b2031ff9cb9e))
