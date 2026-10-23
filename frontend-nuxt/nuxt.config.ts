export default defineNuxtConfig({
  // Define a data de compatibilidade usada pelo Nuxt ao gerar a aplicação.
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  // Folha de estilos global carregada em todas as páginas.
  css: ['~/assets/css/main.css'],
  // Valores de runtime disponíveis no cliente ficam sob `public`.
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000',
    },
  },
  // Metadados partilhados por todas as rotas, aplicados ao <head> da página.
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
