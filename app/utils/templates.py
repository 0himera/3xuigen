HTML_LOGIN_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Тест логина 3xui</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            font-weight: bold;
            margin-bottom: 5px;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #45a049;
        }
        .help-text {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .success-message {
            color: #4CAF50;
            font-weight: bold;
            padding: 10px;
            margin-bottom: 20px;
            background-color: #f2fff2;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Тестирование логина к 3xui</h1>
        <p>Эта форма позволяет протестировать подключение к панели 3xui с разными параметрами.</p>
        
        <div class="success-message">
            ✅ Подключение настроено правильно. Используйте эту форму, если хотите протестировать другие параметры.
        </div>
        
        <form action="/api/xui/manual-login" method="post">
            <div class="form-group">
                <label for="url">URL панели 3xui:</label>
                <input type="text" id="url" name="url" value="http://127.0.0.1:1984/Lq2DsVgcJ9nk2IZ" required>
                <div class="help-text">Укажите полный URL, включая протокол (http:// или https://) и полный путь</div>
            </div>
            
            <div class="form-group">
                <label for="username">Имя пользователя:</label>
                <input type="text" id="username" name="username" value="2zuhi60em2" required>
            </div>
            
            <div class="form-group">
                <label for="password">Пароль:</label>
                <input type="password" id="password" name="password" value="CE53wu3VAL" required>
            </div>
            
            <button type="submit">Проверить логин</button>
        </form>
        
        <div class="help-text" style="margin-top: 20px;">
            <p><strong>Примечание:</strong> После отправки формы вы получите подробный отчет о процессе авторизации.</p>
        </div>
    </div>
</body>
</html>
""" 