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
        price: 100,
        amount: null,
        cut_percentage: 0,
        auto_convert: true
      },
      settings: {
        launch_page: false,
        stripe_key: '',
        fiat: 'USD',
        wallet_id: '',
        title: 'Buy coins',
        description: 'Use your card to pay for coins.',
      },
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
          this.g.user.wallets[0].inkey
        )
        if (!response.data.wallet_id) {
          this.settings.data = response.data
        }
      } catch (err) {
        LNbits.utils.notifyApiError(err)
      }
    },
    async updateSettings() {
      if(
        this.settings.stripe_key && 
        this.settings.fiat &&
        this.settings.wallet_id &&
        this.settings.title &&
        this.settings.description
      ) {
        try {
          await LNbits.api.request(
            'PUT',
            '/sellcoins/api/v1/settings',
            this.g.user.wallets[0].adminkey,
            this.settings.data
          )
          LNbits.utils.notifySuccess('Settings updated successfully')
        } catch (err) {
          LNbits.utils.notifyApiError(err)
        }
      }
      else{
        this.$q.notify({
          type: 'warning',
          message: 'Please complete all fields.'
        })
      }
    },
    async createProduct(productData) {
      try {
        const response = await LNbits.api.request(
          'POST',
          '/sellcoins/api/v1/product',
          this.g.user.wallets[0].adminkey,
          productData
        )
        this.settings.products.push(response.data)
        LNbits.utils.notifySuccess('Product created successfully')
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
        if (response.data.length === 0) {
          this.settings.products = response.data
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
        this.settings.products = this.settings.products.filter(
          pkg => pkg.id !== productId
        )
        LNbits.utils.notifySuccess('Product deleted successfully')
      } catch (err) {
        LNbits.utils.notifyApiError(err)
      }
    },
    async createOrder(orderData) {
      try {
        const response = await LNbits.api.request(
          'POST',
          '/sellcoins/api/v1/order',
          this.g.user.wallets[0].inkey,
          orderData
        )
        this.orders.push(response.data)
        LNbits.utils.notifySuccess('Order created successfully')
      } catch (err) {
        LNbits.utils.notifyApiError(err)
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
    this.settings.wallet_id = this.g.user.walletOptions[0]
    // await this.getSettings()
    //  await this.getProducts();
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
