terraform {
  backend "remote" {
    organization = "girder"

    workspaces {
      name = "dkc-next"
    }
  }
}
provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = ["417138409483"]
  # Must set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY envvars
}
provider "heroku" {
  # Must set HEROKU_EMAIL, HEROKU_API_KEY envvars
}

data "heroku_team" "heroku" {
  # This must be created by hand in the Heroku console
  name = "kitware"
}

resource "aws_route53_zone" "domain" {
  name = "dkc.kitware.com"
}

locals {
  api_fqdn = "api.dkc.kitware.com"
  web_fqdn = "dkc.kitware.com"

  django_cors_origin_whitelist       = ["https://${local.web_fqdn}"]
  django_cors_origin_regex_whitelist = []
}

module "smtp" {
  source  = "girder/girder/aws//modules/smtp"
  version = "0.8.0"

  fqdn            = local.api_fqdn
  project_slug    = "dkc-next"
  route53_zone_id = aws_route53_zone.domain.zone_id
}

resource "random_string" "django_secret" {
  length  = 64
  special = false
}

module "api" {
  source  = "girder/django/heroku//modules/heroku"
  version = "0.8.0"

  team_name = data.heroku_team.heroku.name
  app_name  = "dkc-next"
  fqdn      = local.api_fqdn

  postgresql_plan  = "hobby-basic"

  config_vars = {
    DJANGO_CONFIGURATION               = "HerokuProductionConfiguration"
    DJANGO_ALLOWED_HOSTS               = local.api_fqdn
    DJANGO_CORS_ORIGIN_WHITELIST       = join(",", local.django_cors_origin_whitelist)
    DJANGO_CORS_ORIGIN_REGEX_WHITELIST = join(",", local.django_cors_origin_regex_whitelist)
    DJANGO_DKC_SPA_URL                 = "https://${local.web_fqdn}/"
    DJANGO_DEFAULT_FROM_EMAIL          = "admin@${local.api_fqdn}"
    DJANGO_SENTRY_DSN                  = "https://a9897ae4723d4b0ab90c2856a342ba5a@o267860.ingest.sentry.io/5458971"
    DJANGO_MINIO_STORAGE_ENDPOINT      = "storage.kitware.com:443"
    DJANGO_MINIO_STORAGE_USE_HTTPS     = "true"
    DJANGO_MINIO_STORAGE_ACCESS_KEY    = var.storage_access_key
    DJANGO_MINIO_STORAGE_SECRET_KEY    = var.storage_secret_key
    DJANGO_STORAGE_BUCKET_NAME         = "dkc"
  }
  sensitive_config_vars = {
    DJANGO_EMAIL_URL  = "submission://${urlencode(module.smtp.username)}:${urlencode(module.smtp.password)}@${module.smtp.host}:${module.smtp.port}"
    DJANGO_SECRET_KEY = random_string.django_secret.result
  }
}

resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.domain.zone_id
  name    = local.api_fqdn
  type    = "CNAME"
  ttl     = "300"
  records = [module.api.cname]
}

resource "aws_route53_record" "web" {
  zone_id = aws_route53_zone.domain.zone_id
  name    = local.web_fqdn
  type    = "A"
  ttl     = "300"
  # https://docs.netlify.com/domains-https/custom-domains/configure-external-dns/#configure-an-apex-domain
  records = ["104.198.14.52"]
}
