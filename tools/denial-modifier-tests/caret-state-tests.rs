fn active(version: u32) -> SessionState<u32,u32,u32> {
    let mut state = SessionState::default();
    state.set_focus(Some(Focus { surface: 10, client: 1 }));
    state.register(2, 1, version);
    state.request_enablement(&2, true);
    state.commit(&2);
    state
}
fn rect(y:i32) -> CursorRectangle { CursorRectangle {x:5,y,width:0,height:20} }
fn set(state:&mut SessionState<u32,u32,u32>, value:CursorRectangle) {
    state.set_cursor_rectangle(&2,value); state.commit(&2);
}
#[test] fn absent_is_not_zero_width() {
    let mut state=active(1);
    assert_eq!(state.active_cursor_rectangle(false),None);
    set(&mut state,rect(50));
    assert_eq!(state.active_cursor_rectangle(false),Some(rect(50)));
}
#[test] fn pending_rect_needs_commit() {
    let mut state=active(1); state.set_cursor_rectangle(&2,rect(50));
    assert_eq!(state.active_cursor_rectangle(false),None);
    state.commit(&2); assert_eq!(state.active_cursor_rectangle(false),Some(rect(50)));
}
#[test] fn version_two_needs_matching_surface_commit() {
    let mut state=active(2); set(&mut state,rect(50));
    assert_eq!(state.active_cursor_rectangle(false),None);
    state.surface_committed(&11); assert_eq!(state.active_cursor_rectangle(false),None);
    state.surface_committed(&10); assert_eq!(state.active_cursor_rectangle(false),Some(rect(50)));
}
#[test] fn disable_clears_and_reenable_needs_fresh_rectangle() {
    let mut state=active(1); set(&mut state,rect(50));
    state.request_enablement(&2,false); state.commit(&2);
    assert_eq!(state.active_cursor_rectangle(false),None);
    state.request_enablement(&2,true); state.commit(&2);
    assert_eq!(state.active_cursor_rectangle(false),None);
}
#[test] fn focus_change_clears_even_same_client() {
    let mut state=active(1); set(&mut state,rect(50));
    state.set_focus(Some(Focus {surface:11,client:1}));
    assert_eq!(state.active_cursor_rectangle(false),None);
    state.request_enablement(&2,true); state.commit(&2);
    assert_eq!(state.active_cursor_rectangle(false),None);
}
#[test] fn destroy_clears() {
    let mut state=active(1); set(&mut state,rect(50)); state.remove(&2);
    assert_eq!(state.active_cursor_rectangle(false),None);
}
#[test] fn lock_suppresses() {
    let mut state=active(1); set(&mut state,rect(50));
    assert_eq!(state.active_cursor_rectangle(true),None);
}
#[test] fn same_editor_touch_keeps_caret_without_redundant_rectangle_request() {
    let mut state=active(1); set(&mut state,rect(50));
    state.begin_touch_authorization();
    state.set_content_type(&2, 0, 0);
    state.commit(&2);
    assert_eq!(state.active_cursor_rectangle(false),Some(rect(50)));
}
#[test] fn touch_does_not_destroy_protocol_rectangle() {
    let mut state=active(1); set(&mut state,rect(50)); state.begin_touch_authorization();
    assert_eq!(state.instances[0].current.cursor_rectangle,Some(rect(50)));
}
#[test] fn same_editor_touch_preserves_version_two_surface_commit_contract() {
    let mut state=active(2); set(&mut state,rect(50)); state.begin_touch_authorization();
    assert_eq!(state.active_cursor_rectangle(false),None);
    state.surface_committed(&11);
    assert_eq!(state.active_cursor_rectangle(false),None);
    state.surface_committed(&10);
    assert_eq!(state.active_cursor_rectangle(false),Some(rect(50)));
    state.begin_touch_authorization();
    state.set_surrounding(&2, SurroundingText {text:String::from("test"),cursor:4,anchor:4});
    state.commit(&2);
    assert_eq!(state.active_cursor_rectangle(false),Some(rect(50)));
}
#[test] fn negative_geometry_is_absent() {
    let mut state=active(1); set(&mut state,CursorRectangle{width:-1,..rect(50)});
    assert_eq!(state.active_cursor_rectangle(false),None);
    set(&mut state,CursorRectangle{height:-1,..rect(50)});
    assert_eq!(state.active_cursor_rectangle(false),None);
}
#[test] fn unrelated_client_cannot_change_focused_caret() {
    let mut state=active(1); set(&mut state,rect(50)); state.register(3,4,1);
    state.request_enablement(&3,true); state.set_cursor_rectangle(&3,rect(80)); state.commit(&3);
    assert_eq!(state.active_cursor_rectangle(false),Some(rect(50)));
}
#[test] fn caret_only_change_changes_published_state() {
    let caret=TextInputCaret{window_id:1,surface_id:2,x:5,y:50,width:0,height:20};
    let before=SoftwareKeyboardState{active:true,caret:Some(caret),..SoftwareKeyboardState::default()};
    let after=SoftwareKeyboardState{caret:Some(TextInputCaret{y:80,..caret}),..before};
    assert_ne!(before,after);
}
#[test] fn owner_change_changes_published_state() {
    let caret=TextInputCaret{window_id:1,surface_id:2,x:5,y:50,width:0,height:20};
    let before=SoftwareKeyboardState{active:true,caret:Some(caret),..SoftwareKeyboardState::default()};
    assert_ne!(before,SoftwareKeyboardState{caret:Some(TextInputCaret{surface_id:3,..caret}),..before});
    assert_ne!(before,SoftwareKeyboardState{caret:Some(TextInputCaret{window_id:4,..caret}),..before});
}
#[test] fn activation_change_changes_published_state() {
    let before=SoftwareKeyboardState{active:true,activation_serial:1,..SoftwareKeyboardState::default()};
    assert_ne!(before,SoftwareKeyboardState{activation_serial:2,..before});
}
#[test] fn unlock_cannot_republish_prelock_caret() {
    let mut state=active(1); set(&mut state,rect(50)); state.invalidate_caret();
    assert_eq!(state.active_cursor_rectangle(false),None);
    set(&mut state,rect(80));
    assert_eq!(state.active_cursor_rectangle(false),Some(rect(80)));
}
