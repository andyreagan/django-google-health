> Fetched 2026-05-14 from https://developers.google.com/health/get-started

# Get started | Google Health API

Welcome to the [Google Health API](https://developers.google.com/health)!

This new API leverages Google OAuth, providing a more secure, user-friendly, and scalable solution for accessing and managing health data.

## Benefits

- **Enhanced Security**: The new API aligns with Google's current security recommendations and best practices for API design and implementation, reducing the risk of vulnerabilities.

- **Consistency**: The new API follows modern API design principles, offering a more consistent and intuitive developer experience.

- **Future-proofing**
  - **Scalability**: The new API is designed to scale to meet future demands, supporting a growing number of users and data types.
  - **Maintainability**: Adopting a standardized approach makes it easier to maintain and update apps, reducing technical debt.
  - **Access to new features**: Migrating to the new API provides access to new features and functionalities as they are released, ensuring apps stay current and benefit from the latest advancements.
  - **Compliance**: The new API is kept up-to-date with the latest Google security and privacy standards, reducing the effort required to keep apps compliant.
  - **Data privacy**: The Google OAuth system is designed to comply with various data privacy regulations (for example, GDPR and HIPAA), simplifying the compliance burden on developers.

## How to start?

How you get started with the Google Health API depends on the type of developer you are.

### New developer

If you have no experience with Google APIs or Google Cloud, or need a refresher, the easiest and fastest way to get started is by going through the codelab. It will show you how to set up a Google Cloud project, an OAuth 2.0 web client, and how to use Visual Studio Code to make your first successful call to the Google Health API.

[Go to the codelab](/health/codelabs/make-your-first-api-call#0)

### Fitbit developer

If you are an existing Fitbit Web API developer, you might want to read the migration guide first. It highlights all the differences between the Fitbit Web API and the Google Health API and should provide the guidance you need to start planning your migration.

This guide also highlights best practices and UI samples to assist with guiding your users through the re-authentication process.

After that, either do the codelab, or verify that your Google Cloud setup is complete, before you start development with one of our data type guides.

[Read the migration guide](/health/migration)
[Complete the Google Cloud setup](/health/setup)

## Resources

Beyond getting started, this site features comprehensive resources to assist with development and migration.

- **Support**: Need assistance? Get access to community forums and our public Issue Tracker on the [Support page](/health/support).
- **Google Health API Parity Tool**: [Use this tool](/health/migration/parity-tool) to compare endpoints and functionality between the Fitbit Web API and the Google Health API. It also features a context file you can use directly with an LLM, or as part of an Agents.md file in your preferred AI tool.
- **API reference**: Complete [REST](/health/reference/rest) reference documentation.

**Tip**: Have questions about the content on this page? Use the AI assistance and developer tools to get explanations and clarify your understanding. See [AI assistance and developer tools](/health/ai-assistance-and-developer-tools) to learn more.

---

**Important Note**: To ensure a seamless experience for your users, it is recommended to wait until the end of May 2026 to officially launch your integration to align with legacy Fitbit account deprecation. Please be aware that from now until the end of May, breaking changes may occur as Google responds to developer feedback.
