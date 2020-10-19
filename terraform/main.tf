terraform {
  backend "remote" {
    hostname     = "app.terraform.io"
    organization = "girder"

    workspaces {
      name = "dkc-next"
    }
  }
}
provider "aws" {
  region = "us-east-1"
  allowed_account_ids = ["417138409483"]
  # Must set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY envvars
}
provider "heroku" {
  # Must set HEROKU_EMAIL, HEROKU_API_KEY envvars
}

data "aws_route53_zone" "domain" {
  # This must be created by hand in the AWS console
  name = "girderops.net"
}

data "heroku_team" "heroku" {
  # This must be created by hand in the Heroku console
  name = "metabolomics"
}

module "django" {
  source  = "girder/django/heroku"
  version = "0.5.0"

  project_slug     = "dkc-next"
  route53_zone_id  = data.aws_route53_zone.domain.zone_id
  heroku_team_name = data.heroku_team.heroku.name
  subdomain_name   = "dkc-next"

  additional_django_vars = {
    DJANGO_SENTRY_DSN = "https://a9897ae4723d4b0ab90c2856a342ba5a@o267860.ingest.sentry.io/5458971"
  }
  django_cors_origin_whitelist = ["https://${aws_route53_record.web.fqdn}"]
}

resource "aws_route53_record" "web" {
  zone_id = data.aws_route53_zone.domain.zone_id
  name    = "dkc-next-web"
  type    = "CNAME"
  ttl     = "300"
  records = ["dkc-next.netlify.app"]
}
