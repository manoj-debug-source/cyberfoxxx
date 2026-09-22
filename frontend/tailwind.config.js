export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],

  theme: {
    extend: {

      colors: {
        clear: "#16a34a",
        review: "#d97706",
        reject: "#dc2626",
        brand: "#1f4e78",
        chainValid: "#0ea5e9",
        chainBroken: "#7c2d12",
      },

    },
  },

  plugins: [],
};