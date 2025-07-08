window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  delimiters: ['${', '}'],
  data: function () {
    return {
      products: [],
      wallet: null,
      currencyOptions: [],
      show_product_form: false,
      product: {
        title: 'Buy x coins',
        description: 'Use your card to pay for x coins.',
        price: null,
        amount: null
      },
      settings: {
        denomination: 'USD',
        send_wallet_id: '',         // Added
        receive_wallet_id: '',      // Added
        title: 'Buy coins',
        description: 'Use your card to pay for coins.',
        header_mage: '',            // Added
        haircut: 0,                 // Added
        auto_convert: false,
        email: false,
        email_server: 'smtp.gmail.com',
        email_port: 587,
        email_username: 'yourname@gmail.com',
        email_password: 'your-app-password-here (Use an App Password, not your Gmail password!)',
        email_from: 'yourname@gmail.com',
        email_subject: 'Your coins are ready',
        email_message: 'Your coins are ready to be withdrawn. Scan or click the link below to withdraw your coins.'
      },
      settingsExist: false,
      orders: [],
      currentOrder: null
    }
  },
  methods: {
    async closeFormDialog() {
      this.show_product_form = false
    },
    async getSettings() {
      try {
        const response = await LNbits.api.request(
          'GET',
          '/sellcoins/api/v1/settings',
          this.g.user.wallets[0].adminkey
        )
        this.settings = response.data
        console.log(this.settings)
        this.settingsExist = true
        await this.getProducts();
      } catch (err) {
        LNbits.utils.notifyApiError(err)
      }
    },
    async updateSettings() {
      // Build the settings object with all possible params
      const settings = {
        denomination: this.settings.denomination,
        send_wallet_id: this.settingsExist ? this.settings.send_wallet_id : this.settings.send_wallet_id.value,
        receive_wallet_id: this.settingsExist ? this.settings.receive_wallet_id : this.settings.receive_wallet_id.value,
        title: this.settings.title,
        description: this.settings.description,
        header_mage: this.settings.header_mage,
        haircut: this.settings.haircut,
        auto_convert: this.settings.auto_convert || false,
      };
      if (this.settings.email){
        settings = {
          email: this.settings.email,
          email_server: this.settings.email_server,
          email_port: this.settings.email_port,
          email_username: this.settings.email_username,
          email_password: this.settings.email_password,
          email_from: this.settings.email_from,
          email_subject: this.settings.email_subject,
          email_message: this.settings.email_message
        }
      }
      if (
        settings.denomination &&
        settings.send_wallet_id &&
        settings.receive_wallet_id &&
        settings.title &&
        settings.description &&
        settings.haircut
      ) {
        try {
          
          const response = await LNbits.api.request(
            'PUT',
            '/sellcoins/api/v1/settings',
            this.g.user.wallets[0].adminkey,
            settings
          );
          this.$q.notify({
            message: "Settings updated successfully",
            type: 'positive'
          });
          if (response.data) {
            console.log(response.data);
            this.settings.data = response.data;
          }
        } catch (err) {
          this.$q.notify({
            type: 'warning',
            message: err
          });
        }
      }
    },    
    async createProduct() {
      this.product.settings_id = this.settings.id
      try {
        const response = await LNbits.api.request(
          'POST',
          '/sellcoins/api/v1/product',
          this.g.user.wallets[0].adminkey,
          this.product
        )
        this.products.push(response.data)
        this.$q.notify({
          type: 'positive',
          message: 'Product created successfully'
        });
        this.show_product_form = false
      } catch (err) {
        LNbits.utils.notifyApiError(err)
      }
    },
    async getProducts() {
      try {
        const response = await LNbits.api.request(
          'GET',
          '/sellcoins/api/v1/products',
          this.g.user.wallets[0].inkey
        )
        this.products = response.data
        if (response.data.length === 0) {
          this.products = response.data
        }
      } catch (err) {
        LNbits.utils.notifyApiError(err)
      }
    },
    async deleteProduct(productId) {
      try {
        await LNbits.api.request(
          'DELETE',
          `/sellcoins/api/v1/product/${productId}`,
          this.g.user.wallets[0].adminkey
        )
        await this.getProducts()
      } catch (err) {
        this.$q.notify({
          type: 'positive',
          message: 'Error deleting product: ' + err.message
        });
      }
    },
    async getOrder(orderId) {
      try {
        const response = await LNbits.api.request(
          'GET',
          `/sellcoins/api/v1/order/${orderId}`,
          this.g.user.wallets[0].inkey
        )
        this.currentOrder = response.data
      } catch (err) {
        LNbits.utils.notifyApiError(err)
      }
    },
    async getOrders() {
      try {
        const response = await LNbits.api.request(
          'GET',
          '/sellcoins/api/v1/orders',
          this.g.user.wallets[0].inkey
        )
        this.orders = response.data
      } catch (err) {
        LNbits.utils.notifyApiError(err)
      }
    }
  },
  async created() {
    await this.getSettings()
    LNbits.api
      .request('GET', '/api/v1/currencies')
      .then(response => {
        this.currencyOptions = [LNBITS_DENOMINATION, ...response.data]
      })
      .catch(err => {
        LNbits.utils.notifyApiError(err)
      })
  }
})
