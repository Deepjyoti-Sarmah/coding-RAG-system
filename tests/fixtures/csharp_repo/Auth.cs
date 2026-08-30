namespace App.Auth
{
    public interface IStore
    {
        void Save();
    }

    public class Authenticator : IStore
    {
        private string secret;

        public Authenticator(string secret)
        {
            this.secret = secret;
        }

        public static bool ValidateToken(string token)
        {
            return token.Length > 8;
        }

        public string Login(string user, string token)
        {
            if (ValidateToken(token))
            {
                return SessionFactory.CreateSession(user);
            }
            return "";
        }

        public void Save()
        {
        }
    }
}
