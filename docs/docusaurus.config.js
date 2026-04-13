// @ts-check

const config = {
  title: 'Fabriq',
  tagline: 'Документация ядра моделирования производственных процессов',
  favicon: 'img/favicon.ico',

  url: 'https://de-de-dev.github.io',
  baseUrl: '/Fabriq/',

  organizationName: 'de-de-dev',
  projectName: 'Fabriq',
  trailingSlash: false,

  onBrokenLinks: 'throw',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'ru',
    locales: ['ru'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          routeBasePath: '/',
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'Fabriq',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'coreSidebar',
          position: 'left',
          label: 'Ядро моделирования',
        },
        {
          href: 'https://github.com/de-de-dev/Fabriq',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Разделы',
          items: [
            {
              label: 'Обзор ядра',
              to: '/',
            },
            {
              label: 'Контракт интеграции',
              to: '/integration-contract',
            },
          ],
        },
        {
          title: 'Проект',
          items: [
            {
              label: 'Репозиторий',
              href: 'https://github.com/de-de-dev/Fabriq',
            },
          ],
        },
      ],
      copyright: `Fabriq. Документация ядра моделирования.`,
    },
    prism: {
      additionalLanguages: ['python'],
    },
  },
};

module.exports = config;
