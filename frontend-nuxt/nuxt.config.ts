export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000',
    },
  },
  app: {
    head: {
      title: 'TaskFlow — Projetos académicos, com rumo.',
      meta: [
        {
          name: 'description',
          content: 'Planeia, acompanha e conclui os teus projetos académicos.',
        },
        { name: 'theme-color', content: '#f7f8fc' },
      ],
    },
  },
})
