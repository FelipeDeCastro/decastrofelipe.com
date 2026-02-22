# decastrofelipe.com

Personal portfolio site for Felipe de Castro, Product Designer.

## Stack

- Static HTML/CSS/JS (exported from Webflow)
- Hosted on GitHub Pages

## Structure

```
├── index.html          # Homepage
├── about.html          # About page
├── cases.html          # Project listing
├── *.html              # Individual case study pages
├── assets/
│   ├── css/style.css   # Main stylesheet
│   ├── js/             # jQuery + Webflow runtime
│   └── img/            # Images and media
└── CNAME               # Custom domain config
```

## Local Development

```bash
python3 -m http.server 8080
```

Then open http://localhost:8080.

## Deployment

Push to `main` — GitHub Pages deploys automatically.
