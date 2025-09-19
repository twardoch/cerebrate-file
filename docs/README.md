# Cerebrate File Documentation

This directory contains the documentation for Cerebrate File, built with Jekyll and the Just-the-Docs theme for GitHub Pages.

## View Documentation

The documentation is automatically published at:
https://twardoch.github.io/cerebrate-file/

## Local Development

### Prerequisites

- Ruby 2.7 or higher
- Bundler gem: `gem install bundler`

### Setup

1. Install dependencies:
   ```bash
   cd docs
   bundle install
   ```

2. Serve locally:
   ```bash
   bundle exec jekyll serve
   ```

3. View at: http://localhost:4000/cerebrate-file/

### Alternative with Docker

```bash
docker run --rm \
  -v "$PWD:/srv/jekyll" \
  -p 4000:4000 \
  jekyll/jekyll:3.9 \
  jekyll serve --watch --force_polling
```

## Documentation Structure

```
docs/
├── _config.yml           # Jekyll configuration
├── index.md             # Home page
├── installation.md      # Installation guide
├── usage.md            # Usage guide
├── quick-start.md      # Quick start guide
├── cli-reference.md    # CLI reference
├── configuration.md    # Configuration guide
├── examples.md         # Examples
├── api-reference.md    # API documentation
├── troubleshooting.md  # Troubleshooting
├── development.md      # Development guide
└── Gemfile            # Ruby dependencies
```

## Adding New Pages

1. Create a new `.md` file
2. Add front matter:
   ```yaml
   ---
   layout: default
   title: Page Title
   nav_order: 10
   ---
   ```
3. Write content in Markdown

## Theme Documentation

This site uses the Just-the-Docs theme:
- [Theme documentation](https://just-the-docs.github.io/just-the-docs/)
- [Theme repository](https://github.com/just-the-docs/just-the-docs)

## Deployment

Documentation is automatically deployed to GitHub Pages when pushed to the main branch.

### Manual Deployment

1. Build the site:
   ```bash
   bundle exec jekyll build
   ```

2. The built site is in `_site/`

## Configuration

Key settings in `_config.yml`:
- `remote_theme`: Uses Just-the-Docs theme
- `baseurl`: Set to `/cerebrate-file` for GitHub Pages
- `search_enabled`: Enables built-in search
- `color_scheme`: Light/dark theme

## Contributing

1. Make changes to markdown files
2. Test locally with `bundle exec jekyll serve`
3. Submit pull request

## License

Documentation is licensed under the same Apache 2.0 license as the main project.