const I18n = {
    lang: 'zh',
    strings: {
        zh: {
            login: '登录', register: '注册', login_subtitle: '通过丰富的句子分析掌握英语',
            vocabulary: '词汇', settings: '设置', logout: '退出',
            todays_progress: '今日进度', quick_review: '快速复习', all_levels: '所有级别',
            learn: '学习', read_aloud: '朗读', dictation: '听写',
            learn_hint: '学习句子结构，听发音。', read_aloud_hint: '听并跟读，评价你的发音。',
            dictation_hint: '输入你听到的内容：', submit: '提交',
            good: '好', okay: '一般', again: '再来',
            speed: '速度', repeat: '重复',
            all: '全部', mastered: '已掌握', learning: '学习中', weak: '薄弱',
            flashcard_mode: '闪卡模式', ui_language: 'UI语言', tts_speed: '语速',
            daily_goal: '每日目标', save: '保存',
            score: '得分', correct: '正确', close_match: '接近', missing: '缺少', extra: '多余',
            sentence: '句子', of: '/', lesson: '课程',
            flip: '翻转', next_card: '下一张',
            register_success: '注册成功！请登录。', username_exists: '用户名已存在',
            invalid_credentials: '用户名或密码错误',
            placeholder_username: '用户名', placeholder_password: '密码', placeholder_type: '在这里输入...',
            no_vocabulary_yet: '还没有词汇，完成一些课程后再来看看吧！',
            no_review_items: '没有需要复习的内容，继续学习新课程吧！',
            no_lessons_found: '没有找到课程。',
            all_cards_reviewed: '所有卡片都已复习完成！',
            no_flashcards: '还没有词汇卡片。',
            rating_saved: '评分已保存',
            lesson_complete: '课程完成！', lesson_complete_msg: '你已完成本课所有句子！',
            back_to_dashboard: '返回主页', review_weak: '复习薄弱句子',
            daily_goal_reached: '今日目标达成！',
            try_again: '再试一次',
            btn_vocab: '词汇本', btn_settings: '设置', btn_logout: '退出',
            btn_back: '返回', btn_play: '播放', btn_repeat: '重放',
            btn_prev: '上一句', btn_next: '下一句',
            tap_to_speak: '点击麦克风朗读', listening: '正在听...',
            no_speech_detected: '没有检测到语音，请重试', mic_not_allowed: '请允许使用麦克风',
            speech_not_supported: '您的浏览器不支持语音识别，请使用Chrome',
            pronunciation_score: '发音得分', you_said: '你说的',
            great_pronunciation: '发音很棒！继续保持！', keep_practicing: '不错，继续练习！',
            try_again_speech: '再试一次，注意听原文发音。', or_self_rate: '或自我评价：',
            read_aloud_hint: '先听原文，然后点击麦克风朗读。',
        },
        vi: {
            login: 'Đăng nhập', register: 'Đăng ký', login_subtitle: 'Học tiếng Anh với phân tích câu phong phú',
            vocabulary: 'Từ vựng', settings: 'Cài đặt', logout: 'Đăng xuất',
            todays_progress: 'Tiến độ hôm nay', quick_review: 'Ôn tập nhanh', all_levels: 'Tất cả cấp độ',
            learn: 'Học', read_aloud: 'Đọc', dictation: 'Nghe viết',
            learn_hint: 'Học cấu trúc câu và nghe phát âm.', read_aloud_hint: 'Nghe và lặp lại. Đánh giá phát âm của bạn.',
            dictation_hint: 'Nhập những gì bạn nghe được:', submit: 'Gửi',
            good: 'Tốt', okay: 'Được', again: 'Lại',
            speed: 'Tốc độ', repeat: 'Lặp lại',
            all: 'Tất cả', mastered: 'Đã thông thạo', learning: 'Đang học', weak: 'Yếu',
            flashcard_mode: 'Chế độ thẻ ghi nhớ', ui_language: 'Ngôn ngữ', tts_speed: 'Tốc độ đọc',
            daily_goal: 'Mục tiêu hàng ngày', save: 'Lưu',
            score: 'Điểm', correct: 'Đúng', close_match: 'Gần đúng', missing: 'Thiếu', extra: 'Thừa',
            sentence: 'Câu', of: '/', lesson: 'Bài học',
            flip: 'Lật', next_card: 'Thẻ tiếp theo',
            register_success: 'Đăng ký thành công! Vui lòng đăng nhập.', username_exists: 'Tên người dùng đã tồn tại',
            invalid_credentials: 'Tên người dùng hoặc mật khẩu không đúng',
            placeholder_username: 'Tên người dùng', placeholder_password: 'Mật khẩu', placeholder_type: 'Nhập vào đây...',
            no_vocabulary_yet: 'Chưa có từ vựng nào, hãy hoàn thành một số bài học trước!',
            no_review_items: 'Không có nội dung cần ôn tập, hãy tiếp tục học bài mới!',
            no_lessons_found: 'Không tìm thấy bài học.',
            all_cards_reviewed: 'Đã xem hết tất cả thẻ!',
            no_flashcards: 'Chưa có thẻ từ vựng nào.',
            rating_saved: 'Đã lưu đánh giá',
            lesson_complete: 'Hoàn thành bài học!', lesson_complete_msg: 'Bạn đã hoàn thành tất cả các câu!',
            back_to_dashboard: 'Về trang chính', review_weak: 'Ôn tập câu yếu',
            daily_goal_reached: 'Đạt mục tiêu hôm nay!',
            try_again: 'Thử lại',
            btn_vocab: 'Từ vựng', btn_settings: 'Cài đặt', btn_logout: 'Đăng xuất',
            btn_back: 'Quay lại', btn_play: 'Phát', btn_repeat: 'Phát lại',
            btn_prev: 'Câu trước', btn_next: 'Câu sau',
            tap_to_speak: 'Nhấn micro để đọc', listening: 'Đang nghe...',
            no_speech_detected: 'Không phát hiện giọng nói, hãy thử lại', mic_not_allowed: 'Vui lòng cho phép sử dụng micro',
            speech_not_supported: 'Trình duyệt không hỗ trợ nhận dạng giọng nói, hãy dùng Chrome',
            pronunciation_score: 'Điểm phát âm', you_said: 'Bạn nói',
            great_pronunciation: 'Phát âm tuyệt vời! Tiếp tục phát huy!', keep_practicing: 'Khá tốt, tiếp tục luyện tập!',
            try_again_speech: 'Thử lại, chú ý nghe phát âm gốc.', or_self_rate: 'Hoặc tự đánh giá:',
            read_aloud_hint: 'Nghe trước, sau đó nhấn micro để đọc to.',
        }
    },
    setLang(lang) {
        this.lang = lang;
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (this.strings[lang] && this.strings[lang][key]) el.textContent = this.strings[lang][key];
        });
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            if (this.strings[lang] && this.strings[lang][key]) el.title = this.strings[lang][key];
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (this.strings[lang] && this.strings[lang][key]) el.placeholder = this.strings[lang][key];
        });
        document.querySelectorAll('[data-i18n-option]').forEach(el => {
            const key = el.getAttribute('data-i18n-option');
            if (this.strings[lang] && this.strings[lang][key]) el.textContent = this.strings[lang][key];
        });
    },
    t(key) { return (this.strings[this.lang] && this.strings[this.lang][key]) || key; }
};
