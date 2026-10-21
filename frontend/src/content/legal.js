export const legalContact = {
  operator: "Konstantinos Damianos",
  email: "kostas2372@gmail.com",
  updated: "21 October 2026",
};

export const legalDocuments = {
  privacy: {
    title: "Privacy Policy",
    introduction: "This policy explains how Viddie handles information when you create videos and connect social accounts. Viddie is operated by Konstantinos Damianos. Contact kostas2372@gmail.com with privacy questions or requests.",
    sections: [
      {
        title: "Information we process",
        paragraphs: [
          "Account information includes your username, email address and a password hash. We also process the prompts, scripts, uploaded images, video, audio, voice and avatar information, generated media, project settings and exports you use in Viddie.",
          "If you supply provider API keys, Viddie stores them encrypted and uses them to make the requests you initiate. Generation usage records, publishing history and technical logs help operate the service and investigate errors.",
          "When you connect YouTube, TikTok or Instagram, Viddie receives account identifiers, display names and authorization tokens. It also receives the account capabilities and upload status needed to offer publishing. Viddie does not ask for your social account password.",
        ],
      },
      {
        title: "How information is used",
        paragraphs: [
          "We use this information to provide your account, generate and edit media, render exports, display usage, connect the social accounts you choose, and carry out publishing requests you confirm. We also use relevant technical information to maintain the service, prevent abuse and respond to support requests.",
          "Connecting a social account does not publish a video. You choose the account, review the export and posting options, and confirm each publishing request. Viddie uses connected-platform data for these user-facing functions, not to sell data, target advertising or train general-purpose AI models.",
        ],
      },
      {
        title: "Providers and sharing",
        paragraphs: [
          "When you request generation, the relevant prompt, script or media is sent to the provider selected for that task. Available integrations include OpenAI, Anthropic, Google Gemini, ElevenLabs, 60dB, image-generation services, Google Custom Search and custom providers configured by you or the operator. Only the integrations used for your request receive that request's relevant content. Their own terms and privacy practices apply to the information they receive.",
          "When you confirm publishing, the chosen social platform receives the exported video and the caption, title, visibility, disclosures and other posting settings needed for that request. Instagram retrieves the export through an expiring signed link. Hosting, storage, email and connectivity services may process information needed to deliver Viddie. This local testing deployment uses Cloudflare Tunnel to make the app and callbacks reachable over HTTPS.",
          "Media links may be accessible to people who have the URL. Do not upload sensitive or confidential material to this testing deployment. Platform copies of published content are governed by that platform's policies; deleting something in Viddie does not delete an existing social post.",
          "Viddie uses YouTube API Services. Google's privacy policy is available at https://policies.google.com/privacy. Viddie's use and transfer of information received from Google APIs will adhere to the Google API Services User Data Policy, including its Limited Use requirements. Google API data is not shared with generation providers for model training.",
        ],
      },
      {
        title: "Storage, security and retention",
        paragraphs: [
          "Account and project information is stored in the deployment's database and media storage. Social authorization tokens and saved provider keys are encrypted in the database. Cookies and browser storage support sign-in, session persistence and interface preferences.",
          "Viddie retains projects and exports until you delete them or request their removal. Publishing creates a separate export copy so later edits cannot change an upload already requested. Publishing records and these copies do not currently expire automatically; contact the operator to request their deletion. Removing a social connection deletes its locally stored tokens. Technical logs and any backup copies are managed by the operator and may require separate removal.",
          "Providers may process information in countries other than yours, under their own hosting arrangements and applicable transfer safeguards. Contact the operator for the processing locations, retention arrangements and safeguards for the deployment you use.",
        ],
      },
      {
        title: "Your choices and requests",
        paragraphs: [
          "You can remove projects and uploaded assets using the available controls, replace or remove saved provider keys, and disconnect social accounts from Publish. You can also revoke access in the social platform's account settings. For Google, visit https://myaccount.google.com/permissions. Disconnecting cancels queued publishing requests; a transfer that has already started may still finish.",
          "For account deletion, access, correction, export or deletion of personal information, email kostas2372@gmail.com. We may need to verify that you control the account. There is currently no self-service account-deletion screen. Where applicable law provides them, you may also request restriction, object to processing or withdraw consent, and complain to your data protection authority. Withdrawal does not undo earlier lawful processing.",
          "We process information needed to provide the service you request, rely on your authorization for optional social connections, and use relevant information for legitimate interests such as service security and support, subject to your rights. Legal obligations may require retaining particular records.",
        ],
      },
      {
        title: "Children and policy changes",
        paragraphs: [
          "Viddie is not directed at children. You must meet the age and account requirements of the services you use. Contact the operator if you believe a child has supplied personal information without appropriate authorization.",
          "We will update this page when our practices change. The date above identifies this version. Material changes affecting connected-account access will be explained before requesting any additional authorization.",
        ],
      },
    ],
  },
  terms: {
    title: "Terms of Service",
    introduction: "These terms describe use of Viddie, operated by Konstantinos Damianos. Contact kostas2372@gmail.com with questions. Review these terms and the Privacy Policy before using the service.",
    sections: [
      {
        title: "Using Viddie",
        paragraphs: [
          "Viddie provides tools to create, edit and export videos and, when configured, publish an export to a social account you connect. You must be entitled to use the service and meet the age and account requirements of each connected provider. Keep your sign-in details and provider keys secure and use only accounts you own or are authorized to manage.",
          "This deployment is for development and testing. Features, availability and temporary public addresses may change. Keep your own copies of important material; a test deployment is not an archival service.",
        ],
      },
      {
        title: "Your content and responsibilities",
        paragraphs: [
          "You retain any rights you hold in the content you upload. You authorize Viddie and the providers needed for your chosen tasks to process, store, render and transfer that content to perform those tasks. This permission does not transfer ownership to Viddie.",
          "You are responsible for having the necessary rights and permissions for scripts, footage, images, music, voices, likenesses and other material. Search results and generated content do not guarantee that material is licensed for your intended use. Review outputs for accuracy, permissions, safety and required AI or commercial disclosures before sharing them.",
          "Do not use Viddie for unlawful content, infringement, impersonation, unauthorized voice or likeness use, abuse, or attempts to access other people's accounts or data. Follow each provider's rules and the applicable social platform's content policies.",
        ],
      },
      {
        title: "Social publishing",
        paragraphs: [
          "A social connection grants the permissions shown by the platform. Publishing requires a separate confirmation in Viddie. Check the destination account, exported video, caption, title, visibility, audience settings and disclosures before confirming. Viddie uploads the last completed export selected in the publishing flow.",
          "An upload can fail, be delayed, be restricted to private viewing or be rejected by a platform. A successful upload does not guarantee public visibility. If Viddie reports that an outcome needs checking, inspect the destination before starting another upload to avoid duplicate posts.",
          "You can disconnect an account or revoke platform access. Disconnecting cancels queued requests, but an upload already underway may complete. Delete or change published posts on the destination platform. Viddie does not currently provide scheduling or automatic removal of existing posts.",
        ],
      },
      {
        title: "Third-party services and costs",
        paragraphs: [
          "Generation, search, voice and social services have their own terms, privacy policies, eligibility requirements, usage limits and charges. Requests made with your API keys can incur provider costs. You are responsible for charges under your provider accounts. Viddie's usage display is informational and may differ from the provider's billing records.",
          "Viddie uses YouTube API Services. By using the YouTube integration, you agree to the YouTube Terms of Service at https://www.youtube.com/t/terms. TikTok and Meta integrations are also subject to those platforms' applicable terms. Viddie is not endorsed by these platforms.",
        ],
      },
      {
        title: "Access, support and changes",
        paragraphs: [
          "The operator may restrict access when necessary to investigate abuse, protect the service, comply with law or respond to a provider restriction. You can stop using Viddie at any time and request account or data deletion by emailing kostas2372@gmail.com.",
          "Viddie cannot guarantee uninterrupted operation, error-free generations or that a provider will accept a publishing request. These terms do not exclude rights or remedies that applicable law does not allow us to exclude.",
          "Changes to these terms will be posted here with an updated date. The operator will explain material changes before they apply to your continued use where required. Contact kostas2372@gmail.com for support or questions about these terms.",
        ],
      },
    ],
  },
};
