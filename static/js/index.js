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
        send_wallet_id: '',
        receive_wallet_id: '',
        title: 'Buy coins',
        description: 'Use your card to pay for coins.',
        header_image: '/sellcoins/static/image/bitcoins.png',
        haircut: 0,
        auto_convert: true,
        email: false,
        nostr: false,
        email_message: 'Your coins are ready to be withdrawn. Scan or click the link below to withdraw your coins.',
        launch_page: true,
        live_mode: false
      },
      settingsExist: false,
      orders: [],
      ordersTable: {
        columns: [
          {
            name: 'id',
            align: 'left',
            label: 'ID',
            field: 'id'
          },
          {
            name: 'product_id',
            align: 'left',
            label: 'Product ID',
            field: 'product_id'
          },
          {
            name: 'status',
            align: 'left',
            label: 'Staus',
            field: 'status',
            sortable: true
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
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
        console.log(err)
        console.log(this.settings)
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
        header_image: this.settings.header_image,
        haircut: this.settings.haircut,
        auto_convert: this.settings.auto_convert || false,
        email: this.settings.email,
        nostr: this.settings.nostr,
        email_message: this.settings.email_message,
        launch_page: this.settings.launch_page,
        live_mode: this.settings.live_mode || false
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
    async getOrders() {
      try {
        const response = await LNbits.api.request(
          'GET',
          '/sellcoins/api/v1/orders/' + this.settings.id,
          this.g.user.wallets[0].adminkey
        )
        this.orders = response.data
      } catch (err) {
        console.log(err)
      }
    }
  },
  async created() {
    await this.getSettings()
    if (this.settings.id){
      await this.getOrders()
    }
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
