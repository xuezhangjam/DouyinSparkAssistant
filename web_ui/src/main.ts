import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      dark: {
        colors: {
          primary: '#D0BCFF', // Material You light purple for dark mode
          secondary: '#CCC2DC',
          tertiary: '#EFB8C8',
          background: '#141218',
          surface: '#1D1B20',
          'surface-variant': '#49454F',
          error: '#F2B8B5',
        },
      },
      light: {
        colors: {
          primary: '#6750A4', // Material You Deep Purple
          secondary: '#625B71',
          tertiary: '#7D5260',
          background: '#FEF7FF',
          surface: '#FEF7FF',
          'surface-variant': '#E7E0EC',
          error: '#B3261E',
        }
      }
    },
  },
})

const app = createApp(App)

app.use(router)
app.use(vuetify)

app.mount('#app')
