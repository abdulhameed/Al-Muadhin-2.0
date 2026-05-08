from django.core.management.base import BaseCommand
from django.conf import settings
from apps.providers.models import Country, TelcoProvider, ProviderCountry


class Command(BaseCommand):
    help = 'Seed initial providers for launch countries'

    def handle(self, *args, **options):
        self.stdout.write('Starting provider seeding...')

        # Create countries if they don't exist
        countries_data = {
            'NG': {'name': 'Nigeria', 'dial_code': '+234'},
            'GB': {'name': 'United Kingdom', 'dial_code': '+44'},
            'US': {'name': 'United States', 'dial_code': '+1'},
            'CA': {'name': 'Canada', 'dial_code': '+1'},
            'AE': {'name': 'United Arab Emirates', 'dial_code': '+971'},
        }

        countries = {}
        for code, data in countries_data.items():
            country, created = Country.objects.get_or_create(
                code=code,
                defaults={
                    'name': data['name'],
                    'dial_code': data['dial_code'],
                    'is_supported': True,
                }
            )
            countries[code] = country
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created {country.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'- {country.name} already exists'))

        # Define providers with their configuration
        providers_config = [
            {
                'name': 'Twilio',
                'provider_type': 'both',
                'adapter_class': 'apps.providers.adapters.twilio.TwilioAdapter',
                'cost_per_sms': 0.0075,
                'cost_per_minute': 0.05,
                'currency': 'USD',
                'countries': {
                    'US': 0,
                    'CA': 0,
                },
            },
            {
                'name': 'Vonage',
                'provider_type': 'both',
                'adapter_class': 'apps.providers.adapters.vonage.VonageAdapter',
                'cost_per_sms': 0.0068,
                'cost_per_minute': 0.06,
                'currency': 'USD',
                'countries': {
                    'GB': 0,
                    'US': 1,
                },
            },
            {
                'name': 'Termii',
                'provider_type': 'sms',
                'adapter_class': 'apps.providers.adapters.termii.TermiiAdapter',
                'cost_per_sms': 0.015,
                'cost_per_minute': 0,
                'currency': 'USD',
                'countries': {
                    'NG': 0,
                },
            },
            {
                'name': 'SendGrid',
                'provider_type': 'email',
                'adapter_class': 'apps.providers.adapters.sendgrid.SendGridAdapter',
                'cost_per_sms': 0,
                'cost_per_minute': 0,
                'currency': 'USD',
                'countries': {
                    'US': 0,
                    'GB': 1,
                    'NG': 1,
                    'CA': 1,
                    'AE': 1,
                },
            },
        ]

        # Create providers and map to countries
        for provider_config in providers_config:
            provider, created = TelcoProvider.objects.get_or_create(
                name=provider_config['name'],
                defaults={
                    'provider_type': provider_config['provider_type'],
                    'adapter_class': provider_config['adapter_class'],
                    'cost_per_sms': provider_config['cost_per_sms'],
                    'cost_per_minute': provider_config['cost_per_minute'],
                    'currency': provider_config['currency'],
                    'is_active': True,
                    'supports_voice': provider_config['provider_type'] in ['voice', 'both'],
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created provider: {provider.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'- Provider {provider.name} already exists'))

            # Create country mappings
            for country_code, priority in provider_config['countries'].items():
                country = countries.get(country_code)
                if country:
                    pc, created = ProviderCountry.objects.get_or_create(
                        provider=provider,
                        country=country,
                        defaults={
                            'priority': priority,
                            'is_active': True,
                        }
                    )
                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Mapped {provider.name} to {country.name} (priority: {priority})'
                            )
                        )

        self.stdout.write(self.style.SUCCESS('\n✓ Provider seeding completed!'))
        self.stdout.write(
            self.style.WARNING(
                '\nNote: Add the following environment variables for providers to work:\n'
                '  - TWILIO_ACCOUNT_SID\n'
                '  - TWILIO_AUTH_TOKEN\n'
                '  - VONAGE_API_KEY\n'
                '  - VONAGE_API_SECRET\n'
                '  - TERMII_API_KEY\n'
                '  - SENDGRID_API_KEY\n'
            )
        )
