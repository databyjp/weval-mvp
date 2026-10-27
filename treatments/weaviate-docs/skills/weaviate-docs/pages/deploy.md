Source: https://docs.weaviate.io/deploy

# Deploying Weaviate

Weaviate is available as a hosted service, [Weaviate Cloud (WCD)](/go/console?utm_content=deploy), or as a self managed instance. If you manage your own instance, you can host it locally or with a cloud provider. Self-managed instances use the same Weaviate Database as WCD.

If you are upgrading from a previous version of Weaviate, see the [Migration guide](/deploy/migration) for any changes that may affect your installation.

Weaviate offers multiple deployment options to satisfy your specific use case in production.

This section hosts common deployment topics, including Kubernetes, cloud providers, and best practices, along with detailed tutorials and how-to guides.
Weaviate is designed for:

* **Scalability** – Handle billions of vector data points efficiently.
* **High-Performance Search** – Power AI applications with real-time vector retrieval.
* **Flexible Integrations** – Connect with various machine learning models and data sources.
* **Cloud & On-Prem Deployment** – Deploy on Weaviate Cloud, Kubernetes, or managed cloud services.

## Deployment Options

Choose the best deployment method based on your needs:

[EvaluationDevelopmentProduction

Weaviate Cloud

* From evaluation (free tier) to production
* Shared Cloud (infrastructure managed by Weaviate)
* (Optional) Data replication (high-availability)
* (Optional) Zero-downtime updates](/cloud/manage-clusters/create)[EvaluationDevelopmentProduction

Docker

* For local evaluation & development
* Local inference containers
* Multi-modal models
* Customizable configurations](/deploy/installation-guides/docker-installation)[EvaluationDevelopmentProduction

Kubernetes

* From development to production
* Local inference containers
* Multi-modal models
* Customizable configurations
* Self-deploy or Marketplace deployment
* (Optional) Zero-downtime updates](/deploy/installation-guides/k8s-installation)[EvaluationDevelopmentProduction

AWS

* From evaluation to production
* Shared Cloud (bill through AWS)
* Kubernetes (billed through AWS)
* Self-hosted on EKS](/deploy/installation-guides/aws-marketplace)[EvaluationDevelopmentProduction

GCP Marketplace

* From evaluation to production
* Shared Cloud (bill through GCP)
* Kubernetes (billed through GCP)](/deploy/installation-guides/gcp-marketplace)[EvaluationDevelopmentProduction

DigitalOcean

* Fully managed by DigitalOcean
* Provisioned via the DigitalOcean API
* Daily backups, TLS on every connection
* Currently in public preview](/deploy/installation-guides/digitalocean)

### Methods

In addition to the above deployment methods, we also have the following:

* **[Weaviate Cloud](/cloud)**: Managed services for development and production environments.
* **[Snowpark Container Services](/deploy/installation-guides/spcs-integration)** Deploy Weaviate in Snowflake's Snowpark environment.
* **[Embedded Weaviate](/deploy/installation-guides/embedded)**: Experimental. Embedded Weaviate is a client based tool.

Native Windows support

Although Weaviate can be used on Windows via containerized environments like [Docker](/deploy/installation-guides/docker-installation) or [WSL](https://learn.microsoft.com/en-us/windows/wsl/), we don't offer native Windows support at this time.

## Configuration files

Docker Compose and Kubernetes use `yaml` files to configure Weaviate instances. Docker uses the [`docker-compose.yml`](/deploy/installation-guides/docker-installation) file. Kubernetes relies on [Helm charts](/deploy/installation-guides/k8s-installation#weaviate-helm-chart) and the `values.yaml` file. The Weaviate documentation also calls these files `configuration yaml files`.

If you are self-hosting, consider experimenting on a small scale with Docker and then transferring your configuration to Kubernetes Helm charts when you are more familiar with Weaviate.

## Versions

Version availability across deployment options:

Weaviate version availability may differ across deployment options, Weaviate Cloud generally has the latest versions of all deployment methods.

Unreleased software

DISCLAIMER: Release candidate images and other unreleased software are not supported.

Unreleased software and images may contain bugs. APIs may change. Features under development may be withdrawn or modified. Do not use unreleased software in production.

To run an unreleased version of Weaviate, edit your configuration file to use the unreleased image instead of a generally available image. The [GitHub releases page](https://github.com/weaviate/weaviate/releases/) lists generally available and release candidate builds.

For example, to run a Docker image for a release candidate, edit your `docker-config.yaml` to import the release candidate image.

```yml
image: cr.weaviate.io/semitechnologies/weaviate:1.34.0-rc.1
```

When you try upcoming features, please provide [feedback](https://github.com/weaviate/weaviate/issues/new/choose). Your comments are appreciated and help us to make Weaviate more useful for you.

## Further resources

* [Connect to Weaviate](/weaviate/connections)
* [Weaviate Quickstart](/weaviate/quickstart)

## Questions and feedback

Have a question or feedback? Here's how to reach us.

[Community Forum

Ask questions and connect with other developers on our Community forum.](https://forum.weaviate.io/c/support)[Support

Weaviate Cloud user or customer? Find the right channel on the Support page.](/support)
