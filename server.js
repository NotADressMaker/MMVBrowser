const { app } = require("./src/server/app");

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`mmv-browser listening on ${port}`);
});
