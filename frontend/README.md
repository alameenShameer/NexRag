# Frontend

This directory contains the active NexRag React frontend used with the FastAPI backend in the repository root.

## Development

```powershell
npm install
npm run dev
```

The frontend expects the backend to be available at `http://127.0.0.1:8000`.

## Production Build

```powershell
npm run build
```

Generated build output is written to `build/` and is not intended to be committed for normal feature work.

## Features

- chat interface with markdown rendering
- reasoning and confidence display
- source snippet panel
- live system status panel
- knowledge graph editor entry point
